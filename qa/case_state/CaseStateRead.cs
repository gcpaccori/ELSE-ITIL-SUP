using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Xml.Linq;
using SIELSEAccesoDatos;

// One new exact-row SELECT per preselected QA historical incident.
// Strictly metadata of ITIL.taIncidente, never a related commercial entity.
// Source cohort receipt HMAC must verify before any query and its case hash
// must match the FRESH query result. SQL templates and ranks are frozen.
internal static class CaseStateRead {
 const string Root=@"C:\Temp\ELSE_ITIL_CASESTATE_QA_20261112";
 const string MonthlyRoot=@"C:\Temp\ELSE_ITIL_MONTHEND2026_QA_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.2026-case-bound-current-itil-state.v1";
 const string ProofSchema="else.itil.qa.2026-case-bound-current-state-hmac.v1";
 static readonly int[] Ranks={1,12,23,34,45,56,67,78,89,100};
 static string Hash(byte[] raw)=>Convert.ToHexString(SHA256.HashData(raw)).ToLowerInvariant();
 static string Sha(string text)=>Hash(Encoding.UTF8.GetBytes(text));
 static string Val(DataRow row,string name)=>row.IsNull(name)?"":Convert.ToString(row[name],CultureInfo.InvariantCulture)??"";
 static void Need(bool ok,string code){if(!ok)throw new Exception(code);}
 static DataTable Q(AccesoDatos db,string sql,SqlParameter[] ps) {
    var args=new List<SqlParameter>{
       new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
       new("@params",SqlDbType.NVarChar,110){Value=ps.Length==2 ?
          "@start datetime,@end datetime" :
          "@case bigint,@start datetime,@end datetime"}
    };
    args.AddRange(ps);
    var set=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args.ToArray());
    Need(set!=null&&set.Tables.Count>0,"SQL_NO_RESULT_TABLE");
    return set.Tables[0];
 }
 static SqlParameter[] Window(DateTime a,DateTime b)=>new[]{
   new SqlParameter("@start",SqlDbType.DateTime){Value=a},
   new SqlParameter("@end",SqlDbType.DateTime){Value=b}
 };
 static SqlParameter[] Exact(long id,DateTime a,DateTime b)=>new[]{
   new SqlParameter("@case",SqlDbType.BigInt){Value=id},
   new SqlParameter("@start",SqlDbType.DateTime){Value=a},
   new SqlParameter("@end",SqlDbType.DateTime){Value=b}
 };
 static string Mac(string schema,string source,string receipt,byte[] key)=>
   Convert.ToHexString(HMACSHA256.HashData(key,
     Encoding.UTF8.GetBytes(schema+":"+source+":"+receipt))).ToLowerInvariant();
 static (JsonDocument,string) VerifiedMonthly(string month,byte[] key,string monthlyCodeHash){
    string path=Path.Combine(MonthlyRoot,"monthend_"+month+".private.json");
    var raw=File.ReadAllBytes(path);
    var d=JsonDocument.Parse(raw);
    var p=JsonDocument.Parse(File.ReadAllBytes(path+".proof.json"));
    string schema=d.RootElement.GetProperty("schema").GetString()??"";
    string digest=Hash(raw);
    string source=d.RootElement.GetProperty("source_sha256").GetString()??"";
    Need(schema=="else.itil.qa.2026-monthend100-source.v1","SOURCE_SCHEMA_INVALID");
    Need(source==monthlyCodeHash&&source==(p.RootElement.GetProperty("source_sha256").GetString()??""),
      "SOURCE_CODE_HASH_NOT_VERIFIED");
    Need(digest==(p.RootElement.GetProperty("receipt_sha256").GetString()??""),"SOURCE_RECEIPT_HASH_MISMATCH");
    Need(Mac(schema,source,digest,key)==p.RootElement.GetProperty("hmac_sha256").GetString(),
      "SOURCE_RECEIPT_HMAC_INVALID");
    Need(d.RootElement.GetProperty("read_only").GetBoolean()&&
      !d.RootElement.GetProperty("history_or_resolution_read").GetBoolean()&&
      d.RootElement.GetProperty("selected").GetInt32()==100&&
      d.RootElement.GetProperty("period").GetString()==month[..4]+"-"+month[4..],
      "SOURCE_COHORT_SCOPE_INVALID");
    return (d,digest);
 }
 static int Main(){
   try{
     Directory.CreateDirectory(Root);
     foreach(var k in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
       if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(k))){
         var v=Environment.GetEnvironmentVariable(k,EnvironmentVariableTarget.Machine);
         Need(!string.IsNullOrWhiteSpace(v),"QA_CONNECTOR_CONFIG_MISSING");
         Environment.SetEnvironmentVariable(k,v);
       }
     }
     var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
     string cs=xml.Descendants("connectionStrings").Descendants("add")
       .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
       .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
       ??throw new Exception("QA_ROOT_CONFIG_MISSING");
     Need(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)&&
          cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"QA_ROOT_NOT_ALLOWED");
     using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
     var db=provider.Obtener(eSistema.ITIL,(byte)1);
     Need(db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)&&
          db.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase),
          "QA_ITIL_DATABASE_MISMATCH");
     byte[] key=File.ReadAllBytes(Signer);
     Need(key.Length==32,"QA_HMAC_KEY_INVALID");
     string monthlyCode=Hash(File.ReadAllBytes(Path.Combine(MonthlyRoot,"MonthEnd100Read.cs")));
     string ownCode=Hash(File.ReadAllBytes(Path.Combine(Root,"CaseStateRead.cs")));
     const string cohortSql=@"SELECT TOP(100) CodigoIncidente,FechaSolicitud,CodigoModulo,CodigoEmpresa
       FROM dbo.taIncidente WHERE FechaSolicitud>=@start AND FechaSolicitud<@end
       ORDER BY FechaSolicitud DESC,CodigoIncidente DESC";
     const string exactSql=@"SELECT TOP(2) CodigoIncidente,FechaSolicitud,CodigoEmpresa,
       CodigoServicio,CodigoModulo,CodigoCalificacion,CodigoOrigenIncidente,
       CodigoEstadoIncidente,FechaRespuestaSolucion,FechaCierre
       FROM dbo.taIncidente WHERE CodigoIncidente=@case AND
       FechaSolicitud>=@start AND FechaSolicitud<@end";
     var results=new List<object>();
     var sourceReceipts=new List<object>();
     int changed=0,all=0,closed=0;
     for(int month=1;month<=9;month++){
       var start=new DateTime(2026,month,1);
       var end=start.AddMonths(1);
       string ym="2026"+month.ToString("00",CultureInfo.InvariantCulture);
       var (signedSource,sourceReceiptSha)=VerifiedMonthly(ym,key,monthlyCode);
       var signedRows=signedSource.RootElement.GetProperty("results");
       Need(signedRows.GetArrayLength()==100,"SOURCE_ROWS_NOT_HUNDRED");
       var currentCohort=Q(db,cohortSql,Window(start,end));
       Need(currentCohort.Rows.Count==100,"FRESH_MONTH_LAST100_NOT_HUNDRED");
       foreach(int rank in Ranks){
          var source=signedRows[rank-1];
          long rawId=Convert.ToInt64(currentCohort.Rows[rank-1]["CodigoIncidente"],CultureInfo.InvariantCulture);
          string caseHash=Sha(rawId.ToString(CultureInfo.InvariantCulture));
          Need(caseHash==source.GetProperty("case_sha256").GetString(),"FRESH_COHORT_RANK_DRIFT");
          string sourceModule=source.GetProperty("module_code").GetString()??"";
          string sourceCompany=source.GetProperty("company").GetString()??"";
          Need(Val(currentCohort.Rows[rank-1],"CodigoModulo").TrimEnd()==sourceModule &&
               Val(currentCohort.Rows[rank-1],"CodigoEmpresa")==sourceCompany,
               "FRESH_MONTH_CASE_ROUTE_DRIFT");
          var exact=Q(db,exactSql,Exact(rawId,start,end));
          Need(exact.Rows.Count==1,"FRESH_CASE_ROW_MISSING_OR_DUPLICATE");
          var row=exact.Rows[0];
          Need(Sha(Val(row,"CodigoIncidente"))==caseHash,"EXACT_CASE_JOIN_MISMATCH");
          Need(Val(row,"CodigoModulo").TrimEnd()==sourceModule&&
               Val(row,"CodigoEmpresa")==sourceCompany,
               "FRESH_CASE_ROUTE_DRIFT");
          string status=Val(row,"CodigoEstadoIncidente");
          string classification=Val(row,"CodigoCalificacion");
          string origin=Val(row,"CodigoOrigenIncidente");
          string service=Val(row,"CodigoServicio").TrimEnd();
          Need(status.Length<=32&&classification.Length<=32&&origin.Length<=32&&service.Length<=64,
               "BUSINESS_STATE_CODE_OVERSIZED");
          var fields=new Dictionary<string,object?>{
              ["CodigoEstadoIncidente"]=status,
              ["CodigoModulo"]=sourceModule,
              ["CodigoEmpresa"]=sourceCompany,
              ["CodigoCalificacion"]=classification,
              ["CodigoOrigenIncidente"]=origin,
              ["CodigoServicio"]=service,
              ["FechaCierre.present"]=!row.IsNull("FechaCierre"),
              ["FechaRespuestaSolucion.present"]=!row.IsNull("FechaRespuestaSolucion")
          };
          bool snapshotStatusSame=status==(source.GetProperty("status_code").GetString()??"");
          if(!snapshotStatusSame)changed++;
          if(!row.IsNull("FechaCierre"))closed++;
          all++;
          results.Add(new{
             month=ym[..4]+"-"+ym[4..],rank,
             case_sha256=caseHash,source_month_receipt_sha256=sourceReceiptSha,
             query_id="QA_ITIL_EXACT_INCIDENT_STATE_READ",
             source="ELSE70/dbITIL_D/dbo.taIncidente",
             row_count=1,
             observed_fields=fields,
             snapshot_status_same=snapshotStatusSame,
             read_only=true,
             case_provenance_verified_by_worker=true,
             domain_business_relation_verified=false,
             root_cause_certified=false,repair_certified=false,
             read_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture)
          });
       }
       sourceReceipts.Add(new{month=ym[..4]+"-"+ym[4..],receipt_sha256=sourceReceiptSha,
          original_source_sha256=monthlyCode,selected_rechecked=10});
       signedSource.Dispose();
     }
     Need(all==90,"WRONG_NINETY_READ_COUNT");
     var receipt=new{
        schema=Schema,worker="ELSE62",qa_server="ELSE70",
        source_sha256=ownCode,
        read_scope="EXACT_CASE_STATE_ONLY_NOT_DOMAIN_ENTITY",
        months=9,selected=all,
        first_phase_monthly_receipts=sourceReceipts,
        query_id="QA_ITIL_EXACT_INCIDENT_STATE_READ",
        status_drift_since_source=changed,close_date_present=closed,
        results,read_only=true,business_modifications=0,
        verified_business_domain_links=0,
        read_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture)
     };
     byte[] bytes=JsonSerializer.SerializeToUtf8Bytes(receipt);
     string path=Path.Combine(Root,"case_state_90.private.json");
     File.WriteAllBytes(path,bytes);
     string hash=Hash(bytes);
     File.WriteAllBytes(path+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
       schema=ProofSchema,worker="ELSE62",source_sha256=ownCode,
       receipt_sha256=hash,hmac_sha256=Mac(Schema,ownCode,hash,key),
       read_only=true
     }));
     Console.WriteLine(JsonSerializer.Serialize(new{
         status="EXACT_INCIDENT_QA_STATE_SIGNED",selected=all,
         months=9,distinct_business_domain_links=0,
         status_drift_since_source=changed,close_date_present=closed,
         receipt_sha256=hash,source_sha256=ownCode,
         changes_executed=false
     }));
     return 0;
   }catch(Exception ex){
     Console.Error.WriteLine("CASE_STATE_QA_FAILED:"+ex.GetType().Name+":"+ex.Message);
     return 3;
   }
 }
}
