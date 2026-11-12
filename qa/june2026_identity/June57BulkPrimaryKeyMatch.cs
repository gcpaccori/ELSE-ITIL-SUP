using System;
using System.Data;
using System.Data.SqlClient;
using System.Collections.Generic;
using System.Linq;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using SIELSEAccesoDatos;

// Source-only bulk PK discovery. The cohort's OT/COLLECTION label was
// selected posthoc from historical overlaps: not a blind prediction.
// Only DescripcionSolicitud (no RT numeric blobs, no historical solution)
// is tokenized. The notes are never selected by this reader.
// All DB names/table names/columns are static allowlisted; numbers are
// validated as bigint, passed solely via typed SQL parameters. SELECT ONLY.
internal static class June57BulkPrimaryKeyMatch {
 const string Root=@"C:\Temp\ELSE_ITIL_JUNE57_IDENTIFIER_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string ManifestSchema="else.itil.qa.2026-june57-source-and-history-reference-selection.v1";
 const string ManifestProof="else.itil.qa.2026-june57-source-and-history-reference-hmac.v1";
 const string Schema="else.itil.qa.2026-june57-request-bulk-primary-key-lookup.v1";
 const string Proof="else.itil.qa.2026-june57-request-bulk-primary-key-lookup-hmac.v1";
 const string Reader="June57BulkPrimaryKeyMatch.cs";
 static readonly string[] Databases={
 "dbComercial001_D","dbComercial003_D","dbComercial004_D","dbComercial006_D",
 "dbComercial007_D","dbComercial008_D","dbComercial100_D","dbComercial200_D",
 "dbComercial001_Diario","dbComercial001_20230131","dbComercial003_mayo",
 "dbGerencial_D","dbDistribucion_D"
 };
 static void Need(bool b,string msg){if(!b)throw new Exception(msg);}
 static string Sha(byte[] s)=>Convert.ToHexString(SHA256.HashData(s)).ToLowerInvariant();
 static string Sha(string s)=>Sha(Encoding.UTF8.GetBytes(s));
 static string Val(DataRow r,string c)=>r.IsNull(c)?"":Convert.ToString(r[c],CultureInfo.InvariantCulture)??"";
 static string Mac(byte[] key,string message)=>Convert.ToHexString(HMACSHA256.HashData(key,Encoding.UTF8.GetBytes(message))).ToLowerInvariant();
 static DataTable Q(AccesoDatos db,string query,SqlParameter[]? parameters=null) {
   var args=new List<SqlParameter> {
      new("@stmt",SqlDbType.NVarChar,-1){Value=query},
      new("@params",SqlDbType.NVarChar,-1){Value=parameters is null?"":string.Join(",",
        parameters.Select(p=>p.ParameterName+" bigint"))}
   };
   if(parameters!=null)args.AddRange(parameters);
   var dataset=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args.ToArray());
   Need(dataset!=null&&dataset.Tables.Count>0,"JUNE57_BULK_SQL_NO_RESULT");
   return dataset!.Tables[0];
 }
 static void Main(){
   Directory.CreateDirectory(Root);
   foreach(var env in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
      if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(env))){
        var val=Environment.GetEnvironmentVariable(env,EnvironmentVariableTarget.Machine);
        Need(!string.IsNullOrWhiteSpace(val),"BULK_ID_CORPORATE_CONFIG_MISSING");
        Environment.SetEnvironmentVariable(env,val);
      }
   }
   byte[] key=File.ReadAllBytes(Signer);
   Need(key.Length==32,"BULK_ID_SIGNER_INVALID");
   byte[] manRaw=File.ReadAllBytes(Path.Combine(Root,"june57_manifest.private.json"));
   using var mj=JsonDocument.Parse(manRaw);
   using var pj=JsonDocument.Parse(File.ReadAllBytes(Path.Combine(Root,"june57_manifest.private.json.proof.json")));
   var manifest=mj.RootElement;var proof=pj.RootElement;
   string manSha=Sha(manRaw);
   string sourceSha=manifest.GetProperty("source_sha256").GetString()??"";
   Need(manifest.GetProperty("schema").GetString()==ManifestSchema
     &&proof.GetProperty("schema").GetString()==ManifestProof
     &&proof.GetProperty("receipt_sha256").GetString()==manSha
     &&proof.GetProperty("source_sha256").GetString()==sourceSha
     &&proof.GetProperty("hmac_sha256").GetString()==Mac(key,ManifestSchema+":"+sourceSha+":"+manSha),
     "BULK_ID_MANIFEST_HMAC_INVALID");
   var signed=manifest.GetProperty("rows").EnumerateArray().ToArray();
   var ranks=signed.Select(x=>x.GetProperty("rank").GetInt32()).ToArray();
   Need(signed.Length==57&&ranks.SequenceEqual(ranks.OrderBy(x=>x))
     &&ranks.Distinct().Count()==57
     &&signed.Count(x=>x.GetProperty("category").GetString()=="OT")==22
     &&signed.Count(x=>x.GetProperty("category").GetString()=="COLLECTION")==35,
     "BULK_ID_WRONG_COHORT");
   var doc=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string cfg=doc.Descendants("connectionStrings").Descendants("add")
      .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
      .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
      ??throw new Exception("BULK_ID_ROOT_MISSING");
   Need(cfg.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)
     &&cfg.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"BULK_ID_ROOT_WRONG_QA");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cfg));
   var itil=provider.Obtener(eSistema.ITIL,(byte)1);
   var commercial=provider.Obtener(eSistema.Comercial,(byte)1);
   Need(itil.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
      &&itil.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase)
      &&commercial.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
      &&commercial.cdnConexion.NombreBaseDatos.Equals("dbComercial001_D",StringComparison.OrdinalIgnoreCase),
      "BULK_ID_DATABASE_NOT_QA");
   var query=$@"WITH C AS (
     SELECT ROW_NUMBER() OVER (ORDER BY FechaSolicitud DESC,CodigoIncidente DESC) AS rank,
       CodigoIncidente,CodigoEmpresa,CodigoSucursal,CodigoModulo,
       DescripcionSolicitud FROM dbo.taIncidente
       WHERE FechaSolicitud>=@start AND FechaSolicitud<@end)
     SELECT * FROM C WHERE rank IN ({string.Join(",",ranks)}) ORDER BY rank";
   var args=new[]{
     new SqlParameter("@start",SqlDbType.DateTime){Value=new DateTime(2026,6,1)},
     new SqlParameter("@end",SqlDbType.DateTime){Value=new DateTime(2026,7,1)}
   };
   // This fixed date query uses a separate two-parameter signature.
   var ds=itil.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",new SqlParameter[]{
     new("@stmt",SqlDbType.NVarChar,-1){Value=query},
     new("@params",SqlDbType.NVarChar,-1){Value="@start datetime,@end datetime"},
     args[0],args[1]
   });
   Need(ds!=null&&ds.Tables.Count>0&&ds!.Tables[0].Rows.Count==57,
      "BULK_ID_ORIGINAL_57_NOT_FETCHED");
   var cases=new List<object>();
   var candidateCaseIndex=new Dictionary<string,List<int>>();
   var sourceCaseMeta=new Dictionary<int,(string Category,string ItilBranch,string CaseSha)>();
   var numericalByCategory=new Dictionary<string,HashSet<long>> {
      ["OT"]=new(),["COLLECTION"]=new()
   };
   int valid19=0,invalid19=0;
   foreach(DataRow r in ds!.Tables[0].Rows) {
      int rank=Convert.ToInt32(r["rank"],CultureInfo.InvariantCulture);
      var expected=signed[Array.IndexOf(ranks,rank)];
      string request=Val(r,"DescripcionSolicitud");
      string category=expected.GetProperty("category").GetString()??"";
      string caseSha=Sha(Val(r,"CodigoIncidente"));
      Need(caseSha==expected.GetProperty("case_sha256").GetString()
        &&Sha(request)==expected.GetProperty("request_sha256").GetString()
        &&Val(r,"CodigoEmpresa")==expected.GetProperty("itil_company").GetString()
        &&Val(r,"CodigoModulo").TrimEnd()==expected.GetProperty("module_code").GetString(),
        "BULK_ID_REQUEST_OR_CASE_HASH_DRIFT");
      Need(category=="OT"||category=="COLLECTION","BULK_ID_CATEGORY_NOT_AUTHORIZED");
      var ids=new HashSet<long>();
      foreach(Match match in Regex.Matches(request,@"(?<!\d)\d{19}(?!\d)",
          RegexOptions.CultureInvariant)){
         if(!long.TryParse(match.Value,NumberStyles.None,CultureInfo.InvariantCulture,out long n)){
            invalid19++;continue;
         }
         if(ids.Add(n))valid19++;
      }
      Need(ids.Count<=60,"BULK_ID_TOO_MANY_CANDIDATES_IN_CASE");
      foreach(long id in ids){
         numericalByCategory[category].Add(id);
         string k=category+":"+id.ToString(CultureInfo.InvariantCulture);
         if(!candidateCaseIndex.ContainsKey(k))candidateCaseIndex[k]=new();
         candidateCaseIndex[k].Add(rank);
      }
      sourceCaseMeta[rank]=(category,Val(r,"CodigoSucursal"),caseSha);
      cases.Add(new{
         rank,case_sha256=caseSha,category,
         source_request_sha256=Sha(request),
         itil_branch=Val(r,"CodigoSucursal"),
         request_19digit_bigint_distinct=ids.Count,
         candidate_sha256=ids.Select(x=>Sha(x.ToString(CultureInfo.InvariantCulture))).OrderBy(x=>x).ToArray(),
         historical_note_read=false,
         classification_from_posthoc_fixed_cohort=true
      });
   }
   var online=Q(commercial,@"SELECT name FROM sys.databases
     WHERE name IN ('dbComercial001_D','dbComercial003_D','dbComercial004_D',
     'dbComercial006_D','dbComercial007_D','dbComercial008_D',
     'dbComercial100_D','dbComercial200_D','dbComercial001_Diario',
     'dbComercial001_20230131','dbComercial003_mayo',
     'dbGerencial_D','dbDistribucion_D') AND state_desc='ONLINE'");
   var visible=new HashSet<string>(online.Rows.Cast<DataRow>().Select(x=>Val(x,"name")));
   var matches=new List<object>();
   var skipped=new List<object>();
   int scanQueries=0;
   foreach(string db in Databases) {
      if(!visible.Contains(db)){skipped.Add(new{db,reason="NOT_ONLINE_VISIBLE"});continue;}
      var meta=Q(commercial,$@"SELECT t.name AS table_name FROM [{db}].sys.tables t
          JOIN [{db}].sys.schemas s ON t.schema_id=s.schema_id
          WHERE s.name='dbo' AND t.name IN ('taOrdenTrabajo','taCobranza')");
      var tables=new HashSet<string>(meta.Rows.Cast<DataRow>().Select(x=>Val(x,"table_name")));
      foreach(var cat in new[]{"OT","COLLECTION"}){
         string table=cat=="OT"?"taOrdenTrabajo":"taCobranza";
         string pk=cat=="OT"?"CodigoOrdenTrabajo":"CodigoCobranza";
         if(!tables.Contains(table)){
           skipped.Add(new{db,kind=cat,reason="BUSINESS_TABLE_ABSENT"});continue;
         }
         var numbers=numericalByCategory[cat].OrderBy(x=>x).ToArray();
         for(int start=0;start<numbers.Length;start+=180) {
           var slice=numbers.Skip(start).Take(180).ToArray();
           var ps=slice.Select((x,i)=>new SqlParameter("@k"+i,SqlDbType.BigInt){Value=x}).ToArray();
           var queryDb=$@"SELECT {pk},CodigoSucursal FROM [{db}].dbo.{table}
              WHERE {pk} IN ({string.Join(",",ps.Select(x=>x.ParameterName))})";
           var result=Q(commercial,queryDb,ps);
           scanQueries++;
           Need(result.Rows.Count<=slice.Length,"BULK_ID_NOT_A_UNIQUE_PRIMARY_LOOKUP");
           var valid=new HashSet<long>(slice);
           foreach(DataRow row in result.Rows){
             long found=Convert.ToInt64(row[pk],CultureInfo.InvariantCulture);
             Need(valid.Contains(found),"BULK_ID_RETURNED_NOT_REQUEST_CANDIDATE");
             string k=cat+":"+found.ToString(CultureInfo.InvariantCulture);
             Need(candidateCaseIndex.ContainsKey(k),"BULK_ID_RESULT_NOT_ORIGINATING_FROM_CASE");
             foreach(int rank in candidateCaseIndex[k]) {
               var m=sourceCaseMeta[rank];
               Need(m.Category==cat,"BULK_ID_CASE_CATEGORY_MISMATCH");
               matches.Add(new{
                 rank,case_sha256=m.CaseSha,category=cat,
                 source_candidate_sha256=Sha(found.ToString(CultureInfo.InvariantCulture)),
                 identifier_private=found.ToString(CultureInfo.InvariantCulture),
                 found_in_database=db,
                 business_branch=Val(row,"CodigoSucursal"),
                 itil_branch=m.ItilBranch,
                 business_branch_equals_itil_branch=Val(row,"CodigoSucursal")==m.ItilBranch,
                 current_qa_row_only=true,
                 historical_target_not_read=true,
                 unique_ticket_object_not_proven=true
               });
             }
           }
         }
      }
   }
   Need(scanQueries>0,"BULK_ID_SQL_NEVER_QUERIED");
   string readerSha=Sha(File.ReadAllBytes(Path.Combine(Root,Reader)));
   var resultReceipt=new {
      schema=Schema,source_sha256=readerSha,
      june57_selection_receipt_sha256=manSha,
      qa_itil="ELSE70/dbITIL_D",
      qa_commercial="ELSE70/dbComercial001_D",
      selected_cases=57,
      literal_19digit_bigint_candidates=valid19,
      numeric_overflow_candidates=invalid19,
      distinct_ot_candidate_values=numericalByCategory["OT"].Count,
      distinct_collection_candidate_values=numericalByCategory["COLLECTION"].Count,
      case_metadata=cases,matches,
      scanned_database_count=Databases.Length,
      business_lookup_statements=scanQueries,
      skipped_business_tables=skipped,
      original_request_only=true,
      no_rich_text_numbers_used=true,
      historical_note_column_selected=false,
      case_category_selected_posthoc=true,
      matches_not_historical_execution_proof=true,
      business_writes=0,read_only=true
   };
   byte[] raw=JsonSerializer.SerializeToUtf8Bytes(resultReceipt);
   string digest=Sha(raw);
   string dest=Path.Combine(Root,"june57_bulk_pk_request_matches.private.json");
   File.WriteAllBytes(dest,raw);
   File.WriteAllBytes(dest+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
      schema=Proof,source_sha256=readerSha,receipt_sha256=digest,
      hmac_sha256=Mac(key,Schema+":"+readerSha+":"+digest),
      read_only=true
   }));
   Console.WriteLine(JsonSerializer.Serialize(new{
      status="JUNE57_REQUEST_ONLY_PK_SCAN_PASS",
      input_cases=57,valid19,invalid19,
      query_statements=scanQueries,
      matched_case_db_rows=matches.Count,
      distinct_cases_with_match=matches.Select(x=>JsonSerializer.SerializeToElement(x).GetProperty("rank").GetInt32()).Distinct().Count(),
      receipt_sha256=digest,business_writes=0
   }));
 }
}
