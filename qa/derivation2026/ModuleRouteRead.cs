using System;
using System.Data;
using System.Data.SqlClient;
using System.Globalization;
using System.Text.Json;
using System.Linq;
using System.Xml.Linq;
using System.IO;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;
using SIELSEAccesoDatos;

// The 900 signed ITIL incidents are linked by *same-database primary keys*
// to declared module and service records. AliasBDE and NombreDLL are
// application routing hints; NO foreign business table row is queried.
// No inference AliasBDE => concrete eSistema target is allowed.
internal static class ModuleRouteRead {
 const string Root=@"C:\Temp\ELSE_ITIL_DERIV_CONTRACTS_QA_20261112";
 const string Monthly=@"C:\Temp\ELSE_ITIL_MONTHEND2026_QA_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.2026-module-route-900-contract.v1";
 static string Hash(byte[] data)=>Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();
 static string Sha(string s)=>Hash(Encoding.UTF8.GetBytes(s));
 static void Need(bool pass,string msg){if(!pass)throw new Exception(msg);}
 static string Val(DataRow r,string key)=>r.IsNull(key)?"":Convert.ToString(r[key],CultureInfo.InvariantCulture)??"";
 static string Mac(string schema,string source,string receipt,byte[] key)=>
    Convert.ToHexString(HMACSHA256.HashData(key,
      Encoding.UTF8.GetBytes(schema+":"+source+":"+receipt))).ToLowerInvariant();
 static DataTable Q(AccesoDatos db,string query,SqlParameter[] args,string sig) {
    var p=new List<SqlParameter> {
       new("@stmt",SqlDbType.NVarChar,-1){Value=query},
       new("@params",SqlDbType.NVarChar,80){Value=sig}
    };
    p.AddRange(args);
    var d=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",p.ToArray());
    Need(d!=null&&d.Tables.Count>0,"NO_QA_QUERY_RESULT");
    return d!.Tables[0];
 }
 const string Query=@"WITH C AS (
     SELECT TOP (100)
      CodigoIncidente,FechaSolicitud,CodigoEmpresa,CodigoModulo,
      CodigoServicio,CodigoSistema,CodigoEstadoIncidente
     FROM dbo.taIncidente
     WHERE FechaSolicitud>=@start AND FechaSolicitud<@end
     ORDER BY FechaSolicitud DESC,CodigoIncidente DESC
  )
  SELECT C.CodigoIncidente,C.FechaSolicitud,C.CodigoEmpresa,
       C.CodigoModulo,C.CodigoServicio,C.CodigoSistema,C.CodigoEstadoIncidente,
       M.CodigoModulo AS ResolvedModulo,
       M.CodigoSistema AS ResolvedModuloSistema,
       M.AliasBDE AS DeclaredAliasBDE,
       M.NombreDLL AS DeclaredDLL,
       S.CodigoServicio AS ResolvedServicio
  FROM C
  LEFT JOIN dbo.taModulo M ON M.CodigoModulo=C.CodigoModulo
  LEFT JOIN dbo.taServicio S ON S.CodigoServicio=C.CodigoServicio
  ORDER BY C.FechaSolicitud DESC,C.CodigoIncidente DESC";
 const string Keys=@"SELECT t.name AS T,k.name AS K,c.name AS C,ic.key_ordinal AS Ord
   FROM sys.key_constraints k JOIN sys.tables t ON t.object_id=k.parent_object_id
   JOIN sys.index_columns ic ON ic.object_id=t.object_id AND ic.index_id=k.unique_index_id
   JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
   WHERE k.type='PK' AND t.schema_id=SCHEMA_ID('dbo') AND
     t.name IN ('taModulo','taServicio') AND ic.key_ordinal>0
   ORDER BY t.name,ic.key_ordinal";
 static (JsonDocument,string) SignedSource(string month,string monthlyCode,byte[] key){
   string file=Path.Combine(Monthly,"monthend_"+month+".private.json");
   byte[] raw=File.ReadAllBytes(file);
   var doc=JsonDocument.Parse(raw);
   var p=JsonDocument.Parse(File.ReadAllBytes(file+".proof.json"));
   string digest=Hash(raw);
   var d=doc.RootElement;
   Need(d.GetProperty("schema").GetString()=="else.itil.qa.2026-monthend100-source.v1"
       && d.GetProperty("source_sha256").GetString()==monthlyCode
       && d.GetProperty("period").GetString()==month[..4]+"-"+month[4..]
       && d.GetProperty("selected").GetInt32()==100
       && d.GetProperty("read_only").GetBoolean()
       && !d.GetProperty("history_or_resolution_read").GetBoolean()
       && p.RootElement.GetProperty("receipt_sha256").GetString()==digest
       && p.RootElement.GetProperty("source_sha256").GetString()==monthlyCode
       && Mac("else.itil.qa.2026-monthend100-source.v1",monthlyCode,digest,key)==
          p.RootElement.GetProperty("hmac_sha256").GetString(),
       "SOURCE_COHORT_NOT_SIGNED");
   return (doc,digest);
 }
 static int Main(){
  try{
   Directory.CreateDirectory(Root);
   foreach(var env in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
      if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(env))){
         var v=Environment.GetEnvironmentVariable(env,EnvironmentVariableTarget.Machine);
         Need(!string.IsNullOrWhiteSpace(v),"QA_CONNECTOR_CONFIG_MISSING");
         Environment.SetEnvironmentVariable(env,v);
      }
   }
   var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string cs=xml.Descendants("connectionStrings").Descendants("add")
       .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
       .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
       ??throw new Exception("QA_CONNECTOR_ROOT_NOT_FOUND");
   Need(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)&&
        cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"ROOT_QA_BAD");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
   var db=provider.Obtener(eSistema.ITIL,(byte)1);
   Need(db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
     &&db.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase),
     "DATABASE_QA_NOT_ALLOWLISTED");
   byte[] key=File.ReadAllBytes(Signer);
   Need(key.Length==32,"INVALID_WORKER_HMAC_KEY");
   string sourceSha=Hash(File.ReadAllBytes(Path.Combine(Root,"ModuleRouteRead.cs")));
   string monthlySha=Hash(File.ReadAllBytes(Path.Combine(Monthly,"MonthEnd100Read.cs")));
   var schema=Q(db,Keys,Array.Empty<SqlParameter>(),"");
   var pk=new Dictionary<string,List<string>>(StringComparer.Ordinal);
   foreach(DataRow row in schema.Rows){
      string name=Val(row,"T");
      if(!pk.ContainsKey(name))pk[name]=new();
      pk[name].Add(Val(row,"C"));
   }
   Need(pk.Count==2&&pk["taModulo"].SequenceEqual(new[]{"CodigoModulo"})
      &&pk["taServicio"].SequenceEqual(new[]{"CodigoServicio"}),
      "ROUTE_PK_REQUIREMENTS_UNMET");
   var all=new List<object>();
   var receipts=new List<object>();
   var seen=new HashSet<string>();
   int moduleFound=0,serviceFound=0,aliasPresent=0,dllPresent=0;
   for(int month=1;month<=9;month++){
      string ym="2026"+month.ToString("00",CultureInfo.InvariantCulture);
      var (prior,priorHash)=SignedSource(ym,monthlySha,key);
      receipts.Add(new{month=ym[..4]+"-"+ym[4..],receipt_sha256=priorHash});
      DateTime start=new(2026,month,1),end=start.AddMonths(1);
      var rows=Q(db,Query,new SqlParameter[]{
          new("@start",SqlDbType.DateTime){Value=start},
          new("@end",SqlDbType.DateTime){Value=end}
         },"@start datetime,@end datetime");
      Need(rows.Rows.Count==100,"ROUTE_NOT_100_MONTH_CASES");
      for(int rank=0;rank<100;rank++){
         var v=rows.Rows[rank];
         var orig=prior.RootElement.GetProperty("results")[rank];
         string caseSha=Sha(Val(v,"CodigoIncidente"));
         string module=Val(v,"CodigoModulo").TrimEnd();
         string company=Val(v,"CodigoEmpresa");
         string service=Val(v,"CodigoServicio");
         string system=Val(v,"CodigoSistema");
         Need(orig.GetProperty("case_sha256").GetString()==caseSha &&
              orig.GetProperty("company").GetString()==company &&
              orig.GetProperty("module_code").GetString()==module &&
              orig.GetProperty("status_code").GetString()==Val(v,"CodigoEstadoIncidente") &&
              orig.GetProperty("service_code").GetString()==service &&
              seen.Add(caseSha),"ROUTE_SOURCE_CASE_NOT_BOUND");
         bool foundModule=!v.IsNull("ResolvedModulo");
         bool foundService=!v.IsNull("ResolvedServicio");
         if(foundModule)moduleFound++;if(foundService)serviceFound++;
         Need(!foundModule||Val(v,"ResolvedModulo").TrimEnd()==module,
             "MODULE_CODE_JOIN_INCORRECT");
         Need(!foundService||Val(v,"ResolvedServicio")==service,
             "SERVICE_CODE_JOIN_INCORRECT");
         string alias=Val(v,"DeclaredAliasBDE").Trim();
         string dll=Val(v,"DeclaredDLL").Trim();
         Need(alias.Length<=120&&dll.Length<=255&&module.Length<=32&&
              system.Length<=12,"ROUTE_FIELD_OVERSIZED");
         if(alias.Length>0)aliasPresent++;
         if(dll.Length>0)dllPresent++;
         all.Add(new{
            month=ym[..4]+"-"+ym[4..],rank=rank+1,
            case_sha256=caseSha,month_source_receipt_sha256=priorHash,
            module_code=module,service_code=service,
            case_system_code=system,company_code=company,
            module_row_matched=foundModule,service_row_matched=foundService,
            module_declared_alias_bde=alias,module_declared_dll=dll,
            module_declared_system_code=Val(v,"ResolvedModuloSistema"),
            module_alias_is_database_route_candidate_only=true,
            physical_business_database_verified=false,
            business_object_key_verified=false,
            business_causal_result_verified=false
         });
      }
      prior.Dispose();
   }
   Need(all.Count==900&&seen.Count==900,"ROUTE_NINE_HUNDRED_INVALID");
   var doc=new{
     schema=Schema,source_sha256=sourceSha,
     worker="ELSE62",qa_server="ELSE70",qa_db="dbITIL_D",
     parent="dbo.taIncidente",
     same_database_module_source="dbo.taModulo",
     same_database_service_source="dbo.taServicio",
     declared_pk_metadata_verified=true,
     source_month_receipts=receipts,
     selected=900,months=9,
     module_row_matches=moduleFound,service_row_matches=serviceFound,
     module_alias_present=aliasPresent,module_dll_present=dllPresent,
     module_to_business_entity_fk_certified=false,
     alias_to_physical_db_route_certified=false,
     rows=all,
     read_only=true,modifications=0,
     read_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture)
   };
   byte[] bytes=JsonSerializer.SerializeToUtf8Bytes(doc);
   string dest=Path.Combine(Root,"module_route_900.private.json");
   File.WriteAllBytes(dest,bytes);
   string hash=Hash(bytes);
   string mac=Mac(Schema,sourceSha,hash,key);
   File.WriteAllBytes(dest+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
     schema="else.itil.qa.2026-module-route-900-hmac.v1",worker="ELSE62",
     source_sha256=sourceSha,receipt_sha256=hash,hmac_sha256=mac,read_only=true
   }));
   Console.WriteLine(JsonSerializer.Serialize(new{
      status="MODULE_ROUTE_900_VERIFIED",selected=900,moduleFound,
      serviceFound,aliasPresent,dllPresent,semantic_business_fk=0,
      receipt_sha256=hash
   }));
   return 0;
  }catch(Exception ex) {
    Console.Error.WriteLine("MODULE_ROUTE_QA_FAILED:"+ex.GetType().Name+":"+ex.Message);
    return 3;
  }
 }
}
