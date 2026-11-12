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

// Fixed read-only inspection of QA SQL dictionaries, modules, and SQL object
// *names* that mention the derivation type field. Source SQL definitions are
// NOT exported or trusted as proof of business code semantics.
internal static class DerivationContractsProbe {
 const string Root=@"C:\Temp\ELSE_ITIL_DERIV_CONTRACTS_QA_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Source="ELSE70/dbITIL_D";
 const string Schema="else.itil.qa.2026-derivation-contract-metadata-probe.v1";
 static string Sha(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
 static void Require(bool ok,string c){if(!ok)throw new Exception(c);}
 static string Val(DataRow row,string col)=>row.IsNull(col)?"":Convert.ToString(row[col],CultureInfo.InvariantCulture)??"";
 static DataTable Q(AccesoDatos db,string query){
   var d=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",
      new SqlParameter[]{
         new("@stmt",SqlDbType.NVarChar,-1){Value=query},
         new("@params",SqlDbType.NVarChar,2){Value=""}
      });
   Require(d!=null&&d.Tables.Count>0,"SQL_QA_METADATA_RESULT_MISSING");
   return d!.Tables[0];
 }
 const string DerivColumns=@"SELECT TOP (150) s.name AS S, t.name AS T,
   c.name AS C,ty.name AS DataType
   FROM sys.tables t
   JOIN sys.schemas s ON s.schema_id=t.schema_id
   JOIN sys.columns c ON c.object_id=t.object_id
   JOIN sys.types ty ON ty.user_type_id=c.user_type_id
   WHERE t.name LIKE '%Deriv%' OR c.name LIKE '%TipoDeriv%'
   ORDER BY s.name,t.name,c.column_id";
 const string DictionaryTables=@"SELECT TOP (90) s.name AS S,t.name AS T,
   COUNT(*) AS ColumnCount
   FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
   JOIN sys.columns c ON c.object_id=t.object_id
   WHERE t.name LIKE '%Deriv%' OR t.name LIKE '%Incidente%'
   GROUP BY s.name,t.name ORDER BY s.name,t.name";
 const string DerivCodeReferences=@"SELECT TOP (90) s.name AS S,o.name AS O,
   o.type AS ObjectType,
   CASE WHEN m.definition LIKE '%CodigoTipoDerivacionIncidente%' THEN 1 ELSE 0 END AS UsesTypeCode,
   CASE WHEN m.definition LIKE '%taIncidenteDerivacion%' THEN 1 ELSE 0 END AS UsesDerivationTable,
   CASE WHEN m.definition LIKE '%taOrdenTrabajo%' OR m.definition LIKE '%dbDistribucion%' THEN 1 ELSE 0 END AS UsesDomainOtText
   FROM sys.sql_modules m
   JOIN sys.objects o ON o.object_id=m.object_id
   JOIN sys.schemas s ON s.schema_id=o.schema_id
   WHERE m.definition LIKE '%CodigoTipoDerivacionIncidente%'
      OR m.definition LIKE '%taIncidenteDerivacion%'
   ORDER BY s.name,o.name";
 const string CrossDomainStoredReferences=@"SELECT TOP (75) s.name AS S,o.name AS O,o.type AS ObjectType
   FROM sys.sql_modules m
   JOIN sys.objects o ON o.object_id=m.object_id
   JOIN sys.schemas s ON s.schema_id=o.schema_id
   WHERE (m.definition LIKE '%taIncidente%' OR m.definition LIKE '%CodigoIncidente%')
     AND (m.definition LIKE '%taOrdenTrabajo%' OR m.definition LIKE '%dbDistribucion%'
          OR m.definition LIKE '%dbComercial%' OR m.definition LIKE '%CodigoSuministro%')
   ORDER BY s.name,o.name";
 const string MonthlyModuleMap=@"WITH C AS (
     SELECT CodigoIncidente,FechaSolicitud,CodigoModulo,CodigoSistema,CodigoEmpresa
     FROM dbo.taIncidente
     WHERE FechaSolicitud>='2026-01-01' AND FechaSolicitud<'2026-10-01'
   )
   SELECT TOP(90) RTRIM(C.CodigoModulo) AS Code,
      RTRIM(M.CodigoModulo) AS MatchedCode,M.AliasBDE AS AliasBDE,
      M.NombreDLL AS DLL,M.CodigoSistema AS ModuleSystemCode,
      COUNT_BIG(*) AS Incidents
   FROM C LEFT JOIN dbo.taModulo M ON M.CodigoModulo=C.CodigoModulo
   GROUP BY C.CodigoModulo,M.CodigoModulo,M.AliasBDE,M.NombreDLL,M.CodigoSistema
   ORDER BY COUNT_BIG(*) DESC,RTRIM(C.CodigoModulo)";
 static int Main(){
   try {
     Directory.CreateDirectory(Root);
     foreach(var env in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
       if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(env))){
         string? v=Environment.GetEnvironmentVariable(env,EnvironmentVariableTarget.Machine);
         Require(!string.IsNullOrWhiteSpace(v),"QA_CONFIG_MISSING");
         Environment.SetEnvironmentVariable(env,v);
       }
     }
     var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
     string cs=xml.Descendants("connectionStrings").Descendants("add")
       .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
       .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
       ??throw new Exception("QA_ROOT_CONNECTOR_NOT_AVAILABLE");
     Require(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)&&
       cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"QA_WRONG_ROOT");
     using IConexionBD p=new ConexionBD(new CadenaConexionCollection(cs));
     var db=p.Obtener(eSistema.ITIL,(byte)1);
     Require(db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
       && db.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase),
       "QA_WRONG_ROUTE");
     var columns=Q(db,DerivColumns);
     var tables=Q(db,DictionaryTables);
     var moduleNames=Q(db,DerivCodeReferences);
     var cross=Q(db,CrossDomainStoredReferences);
     var moduleAliases=Q(db,MonthlyModuleMap);
     var fileSha=Sha(File.ReadAllBytes(Path.Combine(Root,"DerivationContractsProbe.cs")));
     var report=new{
       schema=Schema,source_sha256=fileSha,worker="ELSE62",qa_source=Source,
       derivation_related_columns=columns.Rows.Cast<DataRow>().Select(x=>new{
        schema=Val(x,"S"),table=Val(x,"T"),column=Val(x,"C"),data_type=Val(x,"DataType")}).ToArray(),
       dictionary_candidate_tables=tables.Rows.Cast<DataRow>().Select(x=>new{
        schema=Val(x,"S"),table=Val(x,"T"),column_count=Convert.ToInt32(x["ColumnCount"])}).ToArray(),
       stored_logic_objects_referencing_derivation=moduleNames.Rows.Cast<DataRow>().Select(x=>new{
        schema=Val(x,"S"),name=Val(x,"O"),type=Val(x,"ObjectType"),
        uses_type_code=Val(x,"UsesTypeCode")=="1",
        uses_derivation_table=Val(x,"UsesDerivationTable")=="1",
        mentions_domain_ot=Val(x,"UsesDomainOtText")=="1"}).ToArray(),
       stored_logic_objects_cross_domain_candidate=cross.Rows.Cast<DataRow>().Select(x=>new{
        schema=Val(x,"S"),name=Val(x,"O"),type=Val(x,"ObjectType")}).ToArray(),
       module_route_aliases_sample=moduleAliases.Rows.Cast<DataRow>().Select(x=>new{
        module_code=Val(x,"Code"),matched_module_code=Val(x,"MatchedCode"),
        alias_bde=Val(x,"AliasBDE"),assembly=Val(x,"DLL"),
        module_system_code=Val(x,"ModuleSystemCode"),
        incidents=Convert.ToInt64(x["Incidents"],CultureInfo.InvariantCulture)}).ToArray(),
       sql_definition_text_extracted=false,
       no_business_values_read=true,read_only=true,business_modifications=0,
       dictionary_semantics_certified=false,
       app_module_to_business_row_link_certified=false,
       read_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture)
     };
     byte[] content=JsonSerializer.SerializeToUtf8Bytes(report);
     string path=Path.Combine(Root,"derivation_contracts_metadata.private.json");
     File.WriteAllBytes(path,content);
     string hash=Sha(content);
     byte[] key=File.ReadAllBytes(Signer);
     Require(key.Length==32,"QA_HMAC_KEY_INVALID");
     string mac=Convert.ToHexString(HMACSHA256.HashData(key,
       Encoding.UTF8.GetBytes(Schema+":"+fileSha+":"+hash))).ToLowerInvariant();
     File.WriteAllBytes(path+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
      schema="else.itil.qa.2026-derivation-contracts-metadata-hmac.v1",
      worker="ELSE62",source_sha256=fileSha,receipt_sha256=hash,
      hmac_sha256=mac,read_only=true
     }));
     Console.WriteLine(JsonSerializer.Serialize(new{
       status="QA_METADATA_PROBE_SIGNED",
       columns=columns.Rows.Count,dictionary_tables=tables.Rows.Count,
       stored_objects_derivation=moduleNames.Rows.Count,
       stored_objects_cross_domain=cross.Rows.Count,
       module_alias_sample=moduleAliases.Rows.Count,
       receipt_sha256=hash,
       no_business_values_read=true}));
     return 0;
   }catch(Exception ex){
     Console.Error.WriteLine("QA_DERIVATION_PROBE_FAILED:"+ex.GetType().Name+":"+ex.Message);
     return 3;
   }
 }
}
