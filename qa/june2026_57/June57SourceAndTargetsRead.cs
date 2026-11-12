using System;
using System.Data;
using System.Data.SqlClient;
using System.Collections.Generic;
using System.Linq;
using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.IO;
using System.Xml.Linq;
using SIELSEAccesoDatos;

// Bounded evidence-only posthoc follow-up of 22 OT + 35 collections.
// Read-only 57 signed ITIL cases; NEVER executes SQL found in notes.
internal static class June57SourceAndTargetsRead {
 const string Root=@"C:\Temp\ELSE_ITIL_JUNE57_20261112";
 const string KeyFile=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string ManifestSchema="else.itil.qa.2026-june57-source-and-history-reference-selection.v1";
 const string ManifestProof="else.itil.qa.2026-june57-source-and-history-reference-hmac.v1";
 const string Schema="else.itil.qa.2026-june57-business-candidate-scan.v1";
 const string Proof="else.itil.qa.2026-june57-business-candidate-scan-hmac.v1";
 const string Filename="June57SourceAndTargetsRead.cs";
 static readonly string[] DB={
  "dbComercial001_D","dbComercial003_D","dbComercial004_D","dbComercial006_D",
  "dbComercial007_D","dbComercial008_D","dbComercial100_D","dbComercial200_D",
  "dbComercial001_Diario","dbComercial001_20230131","dbComercial003_mayo",
  "dbGerencial_D","dbDistribucion_D"
 };
 static string Hash(byte[] s)=>Convert.ToHexString(SHA256.HashData(s)).ToLowerInvariant();
 static string Hash(string s)=>Hash(Encoding.UTF8.GetBytes(s));
 static string Hmac(byte[] key,string msg)=>Convert.ToHexString(HMACSHA256.HashData(key,Encoding.UTF8.GetBytes(msg))).ToLowerInvariant();
 static void Need(bool b,string e){if(!b)throw new Exception(e);}
 static string Val(DataRow r,string k)=>r.IsNull(k)?"":Convert.ToString(r[k],CultureInfo.InvariantCulture)??"";
 static string? Date(DataRow r,string k)=>r.IsNull(k)?null:
   r[k] is DateTime d?d.ToString("O",CultureInfo.InvariantCulture):Val(r,k);
 static DataTable Q(AccesoDatos db,string sql,string signature="",params SqlParameter[] parameters){
   var args=new List<SqlParameter>{
     new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
     new("@params",SqlDbType.NVarChar,100){Value=signature}
   };
   args.AddRange(parameters);
   var data=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args.ToArray());
   Need(data!=null&&data.Tables.Count>0,"JUNE57_QUERY_NO_TABLE");
   return data!.Tables[0];
 }
 static string FindStrict(string text,string category,bool historical) {
   string pattern=category=="OT"?
    (historical?@"(?i)\bCodigoOrdenTrabajo\s*=\s*'?(\d{9,19})":
        @"(?i)\b(?:CodigoOrdenTrabajo|orden(?:es)?\s+de\s+trabajo|OT)\s*(?:N[°ºo.]?\s*)?[:#=\s-]*(\d{9,19})"):
    (historical?@"(?i)\bCodigoCobranza\s*=\s*'?(\d{9,19})":
        @"(?i)\b(?:CodigoCobranza|cobranza\s+(?:n[uú]mero|nro|c[oó]digo))\s*(?:N[°ºo.]?\s*)?[:#=\s-]*(\d{9,19})");
   var matches=Regex.Matches(text,pattern,RegexOptions.IgnoreCase|RegexOptions.CultureInvariant)
      .Select(x=>x.Groups[1].Value).Distinct().ToArray();
   return matches.Length==0?"":matches.Length==1?matches[0]:"MULTIPLE";
 }
 static void Main(){
   Directory.CreateDirectory(Root);
   foreach(var k in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
      if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(k))){
        var v=Environment.GetEnvironmentVariable(k,EnvironmentVariableTarget.Machine);
        Need(!string.IsNullOrWhiteSpace(v),"JUNE57_QA_ENV_MISSING");
        Environment.SetEnvironmentVariable(k,v);
      }
   }
   byte[] key=File.ReadAllBytes(KeyFile);
   Need(key.Length==32,"JUNE57_HMAC_KEY_INVALID");
   byte[] manRaw=File.ReadAllBytes(Path.Combine(Root,"june57_manifest.private.json"));
   using var manJson=JsonDocument.Parse(manRaw);
   using var mp=JsonDocument.Parse(File.ReadAllBytes(Path.Combine(Root,"june57_manifest.private.json.proof.json")));
   var manifest=manJson.RootElement;
   var proof=mp.RootElement;
   string manSha=Hash(manRaw);
   string manifestCodeSha=manifest.GetProperty("source_sha256").GetString()??"";
   Need(manifest.GetProperty("schema").GetString()==ManifestSchema
     &&proof.GetProperty("schema").GetString()==ManifestProof
     &&proof.GetProperty("source_sha256").GetString()==manifestCodeSha
     &&proof.GetProperty("receipt_sha256").GetString()==manSha
     &&proof.GetProperty("hmac_sha256").GetString()==Hmac(key,
       ManifestSchema+":"+manifestCodeSha+":"+manSha),
     "JUNE57_MANIFEST_NOT_SIGNED");
   var signed=manifest.GetProperty("rows").EnumerateArray().ToArray();
   Need(signed.Length==57 && manifest.GetProperty("selected").GetInt32()==57
       && signed.Count(x=>x.GetProperty("category").GetString()=="OT")==22
       && signed.Count(x=>x.GetProperty("category").GetString()=="COLLECTION")==35,
       "JUNE57_NOT_22_OT_35_COLLECTION");
   int[] ranks=signed.Select(x=>x.GetProperty("rank").GetInt32()).ToArray();
   Need(ranks.Distinct().Count()==57&&ranks.All(x=>x>=1&&x<=1621)
       &&ranks.SequenceEqual(ranks.OrderBy(x=>x)),"JUNE57_WRONG_RANK_SELECTION");
   var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string root=xml.Descendants("connectionStrings").Descendants("add")
     .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
     .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
     ??throw new Exception("JUNE57_QA_ROOT_NOT_FOUND");
   Need(root.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)
        &&root.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"JUNE57_NOT_QA_ROOT");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(root));
   var itil=provider.Obtener(eSistema.ITIL,(byte)1);
   var commercial=provider.Obtener(eSistema.Comercial,(byte)1);
   Need(itil.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
     &&itil.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase)
     &&commercial.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
     &&commercial.cdnConexion.NombreBaseDatos.Equals("dbComercial001_D",StringComparison.OrdinalIgnoreCase),
     "JUNE57_QA_ROUTE_NOT_ALLOWED");
   var query=$@"WITH X AS (
     SELECT ROW_NUMBER() OVER (ORDER BY FechaSolicitud DESC,CodigoIncidente DESC) AS rank,
     CodigoIncidente,CodigoEmpresa,CodigoModulo,FechaSolicitud,DescripcionSolicitud,
     DescripcionSolucion FROM dbo.taIncidente
     WHERE FechaSolicitud>=@start AND FechaSolicitud<@end )
     SELECT * FROM X WHERE rank IN ({string.Join(",",ranks)}) ORDER BY rank";
   var rows=Q(itil,query,"@start datetime,@end datetime",
      new("@start",SqlDbType.DateTime){Value=new DateTime(2026,6,1)},
      new("@end",SqlDbType.DateTime){Value=new DateTime(2026,7,1)});
   Need(rows.Rows.Count==57,"JUNE57_SIGNED_57_NOT_FETCHED");
   var cohort=new List<object>();
   var lookups=new Dictionary<string,List<(int Rank,string Id,string Type)>>();
   foreach(DataRow rec in rows.Rows){
      int rank=Convert.ToInt32(rec["rank"]);
      int i=Array.IndexOf(ranks,rank);
      Need(i>=0,"JUNE57_NOT_IN_SELECTION");
      var expected=signed[i];
      var request=Val(rec,"DescripcionSolicitud");
      var historical=Val(rec,"DescripcionSolucion");
      string cat=expected.GetProperty("category").GetString()??"";
      string caseSha=Hash(Val(rec,"CodigoIncidente"));
      Need(expected.GetProperty("case_sha256").GetString()==caseSha
         &&expected.GetProperty("request_sha256").GetString()==Hash(request)
         &&expected.GetProperty("history_sha256").GetString()==Hash(historical)
         &&expected.GetProperty("module_code").GetString()==Val(rec,"CodigoModulo").TrimEnd()
         &&expected.GetProperty("itil_company").GetString()==Val(rec,"CodigoEmpresa"),
         "JUNE57_CASE_SOURCE_OR_HISTORY_TAMPERED");
      string req=FindStrict(request,cat,false);
      string hist=FindStrict(historical,cat,true);
      string status=req=="MULTIPLE"||hist=="MULTIPLE"?"AMBIGUOUS_IDENTIFIER":
         req!=""&&hist!=""&&req!=hist?"CONFLICT_REQUEST_HISTORICAL_IDS":
         req!=""&&hist!=""?"REQUEST_AND_NOTE_SAME_ID":
         req!=""?"REQUEST_ONLY_PK":
         hist!=""?"HISTORICAL_NOTE_ONLY_PK":
         "NO_EXPLICIT_PRIMARY_KEY";
      string id=status=="REQUEST_AND_NOTE_SAME_ID"||status=="REQUEST_ONLY_PK"?req:
        status=="HISTORICAL_NOTE_ONLY_PK"?hist:"";
      if(id!=""){
         Need(Regex.IsMatch(id,@"^\d{9,19}$")&&long.TryParse(id,out _),
              "JUNE57_IDENTIFIER_INVALID");
         if(!lookups.ContainsKey(cat))lookups[cat]=new();
         lookups[cat].Add((rank,id,cat));
      }
      cohort.Add(new{
         rank,case_sha256=caseSha,category=cat,
         itil_company=Val(rec,"CodigoEmpresa"),
         source_request_identifier_present=req!=""&&req!="MULTIPLE",
         historical_note_identifier_present=hist!=""&&hist!="MULTIPLE",
         identifier_agreement=status=="REQUEST_AND_NOTE_SAME_ID",
         identity_status=status,
         identifier_private=id,identifier_sha256=id==""?"":Hash(id),
         opened_month="2026-06"
      });
   }
   Need(cohort.Count==57,"JUNE57_COHORT_NOT_ALL");
   var dbTable=Q(commercial,@"SELECT name FROM sys.databases
      WHERE name IN ('dbComercial001_D','dbComercial003_D','dbComercial004_D',
      'dbComercial006_D','dbComercial007_D','dbComercial008_D',
      'dbComercial100_D','dbComercial200_D','dbComercial001_Diario',
      'dbComercial001_20230131','dbComercial003_mayo','dbGerencial_D','dbDistribucion_D')
      AND state_desc='ONLINE'");
   var visible=new HashSet<string>(dbTable.Rows.Cast<DataRow>().Select(x=>Val(x,"name")));
   var scan=new List<object>();
   int positiveDbCaseMatches=0;
   var matchedCases=new HashSet<int>();
   int readErrors=0;
   foreach(string db in DB){
      var tbl=new Dictionary<string,bool>();
      if(!visible.Contains(db)){
         scan.Add(new{db,metadata="NOT_VISIBLE_ONLINE",tables=tbl,results=Array.Empty<object>()});
         continue;
      }
      try {
         var metadata=Q(commercial,$@"SELECT t.name FROM [{db}].sys.tables t
           JOIN [{db}].sys.schemas s ON t.schema_id=s.schema_id
           WHERE s.name='dbo' AND t.name IN ('taOrdenTrabajo','taCobranza')");
         foreach(string table in new[]{"taOrdenTrabajo","taCobranza"})
           tbl[table]=metadata.Rows.Cast<DataRow>().Any(x=>Val(x,"name")==table);
      }catch(Exception){
         scan.Add(new{db,metadata="ACCESS_DENIED",tables=tbl,results=Array.Empty<object>()});continue;
      }
      var matches=new List<object>();
      foreach(string category in new[]{"OT","COLLECTION"}){
         string table=category=="OT"?"taOrdenTrabajo":"taCobranza";
         if(!tbl[table])continue;
         if(!lookups.TryGetValue(category,out var keys))continue;
         string field=category=="OT"?"CodigoOrdenTrabajo":"CodigoCobranza";
         foreach(var x in keys){
            try{
                string sql=category=="OT"?
                  (db=="dbDistribucion_D"?
                    $@"SELECT TOP(3) CodigoOrdenTrabajo,CodigoSucursal,CodigoEstadoOrdenTrabajo,
                      CAST(NULL AS tinyint) AS CodigoCentroAtencion,CodigoSubTipoOrdenTrabajo,FechaCreacion,FechaModificacion
                      FROM [{db}].dbo.taOrdenTrabajo WHERE CodigoOrdenTrabajo=@id":
                    $@"SELECT TOP(3) CodigoOrdenTrabajo,CodigoSucursal,CodigoEstadoOrdenTrabajo,
                      CodigoCentroAtencion,CodigoSubTipoOrdenTrabajo,FechaCreacion,FechaModificacion
                      FROM [{db}].dbo.taOrdenTrabajo WHERE CodigoOrdenTrabajo=@id"):
                  $@"SELECT TOP(3) CodigoCobranza,CodigoSucursal,CodigoSucursalDestino,
                      CodigoCaja,FechaCobranza,FechaCancelacion,FechaCreacion,FechaModificacion
                      FROM [{db}].dbo.taCobranza WHERE CodigoCobranza=@id";
                var tab=Q(commercial,sql,"@id bigint",
                    new SqlParameter("@id",SqlDbType.BigInt){Value=long.Parse(x.Id,CultureInfo.InvariantCulture)});
                if(tab.Rows.Count>0) {
                   positiveDbCaseMatches++;
                   matchedCases.Add(x.Rank);
                   var matchRows=new List<object>();
                   foreach(DataRow r in tab.Rows){
                     matchRows.Add(category=="OT"?(object)new{
                       company_branch=Val(r,"CodigoSucursal"),
                       state=Val(r,"CodigoEstadoOrdenTrabajo"),
                       center=Val(r,"CodigoCentroAtencion"),
                       subtype=Val(r,"CodigoSubTipoOrdenTrabajo"),
                       created_month=(Date(r,"FechaCreacion")??"")[..Math.Min(7,(Date(r,"FechaCreacion")??"").Length)],
                       modified_month=(Date(r,"FechaModificacion")??"")[..Math.Min(7,(Date(r,"FechaModificacion")??"").Length)]
                     }:new{
                       company_branch=Val(r,"CodigoSucursal"),
                       destination_branch=Val(r,"CodigoSucursalDestino"),
                       cashbox_code_present=Val(r,"CodigoCaja")!="",
                       collection_month=(Date(r,"FechaCobranza")??"")[..Math.Min(7,(Date(r,"FechaCobranza")??"").Length)],
                       cancelled_month=(Date(r,"FechaCancelacion")??"")[..Math.Min(7,(Date(r,"FechaCancelacion")??"").Length)],
                       modified_month=(Date(r,"FechaModificacion")??"")[..Math.Min(7,(Date(r,"FechaModificacion")??"").Length)]
                     });
                   }
                   matches.Add(new{
                     rank=x.Rank,category,
                     id_sha256=Hash(x.Id),
                     found_rows=tab.Rows.Count,
                     truncated=tab.Rows.Count==3,
                     snapshot=matchRows,
                     source_transaction_not_certified=true
                   });
                }
            }catch(Exception){
               readErrors++;
               matches.Add(new{
                 rank=x.Rank,category,id_sha256=Hash(x.Id),
                 found_rows=-1,truncated=false,snapshot=Array.Empty<object>(),
                 query_error=true,source_transaction_not_certified=true
               });
            }
         }
      }
      scan.Add(new{db,metadata="VISIBLE",tables=tbl,results=matches});
   }
   string codeSha=Hash(File.ReadAllBytes(Path.Combine(Root,Filename)));
   var final=new{schema=Schema,source_sha256=codeSha,
      signed_selection_sha256=manSha,
      june1621_request_sha256=manifest.GetProperty("source_june1621_receipt_sha256").GetString(),
      june1621_history_sha256=manifest.GetProperty("history_june1621_receipt_sha256").GetString(),
      qa_itil="ELSE70/dbITIL_D",
      qa_commercial_access="ELSE70/dbComercial001_D",
      all_57_original_cases_hmac_bound=true,
      case_count=57,ot_count=22,collection_count=35,
      case_identity_data=cohort,
      searched_databases=scan,
      no_historical_sql_executed=true,
      current_state_not_june_asof=true,
      business_repairs_certified=0,business_writes=0,read_only=true};
   byte[] raw=JsonSerializer.SerializeToUtf8Bytes(final);
   string digest=Hash(raw);
   string output=Path.Combine(Root,"june57_business_candidates.private.json");
   File.WriteAllBytes(output,raw);
   File.WriteAllBytes(output+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
      schema=Proof,source_sha256=codeSha,receipt_sha256=digest,
      hmac_sha256=Hmac(key,Schema+":"+codeSha+":"+digest),read_only=true
   }));
   Console.WriteLine(JsonSerializer.Serialize(new{
      status="JUNE57_CORPORATE_SCAN_PASS",selected=57,
      valid_lookup_keys=lookups.Values.Sum(x=>x.Count),
      database_scans=scan.Count,
      positive_database_case_matches=positiveDbCaseMatches,
      distinct_cases_with_match=matchedCases.Count,
      exact_case_query_errors=readErrors,
      receipt_sha256=digest,source_code_sha256=codeSha
   }));
 }
}
