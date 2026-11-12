// ELSE-ITIL-SUP QA: first ten March-2026 ITIL incidents by FechaSolicitud,CodigoIncidente.
// Bound SQL dates, fixed ten rows, no historic solutions and no business modifications.
using System;
using System.Data;
using System.Data.SqlClient;
using System.Linq;
using System.Collections.Generic;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using System.IO;
using SIELSEAccesoDatos;
internal static class MayFirst100Read {
 const string Schema="else.itil.qa.may2026-first100-real-sql.v1";
 const string ProofSchema="else.itil.qa.may2026-first100-hmac.v1";
 const string Root=@"C:\Temp\ELSE_ITIL_MAY100_QA_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 static readonly DateTime Start=new(2026,5,1);
 static readonly DateTime End=new(2026,6,1);
 static string Hash(byte[] bytes)=>Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
 static string Sha(string s)=>Hash(Encoding.UTF8.GetBytes(s));
 static string Val(DataRow r,string name)=>r.IsNull(name)?"":Convert.ToString(r[name],CultureInfo.InvariantCulture)??"";
 static void Require(bool condition,string code){if(!condition)throw new Exception(code);}
 static DataTable Q(AccesoDatos db,string query,SqlParameter[] extras) {
   var args=new List<SqlParameter>{
     new("@stmt",SqlDbType.NVarChar,-1){Value=query},
     new("@params",SqlDbType.NVarChar,80){Value="@start datetime, @end datetime"},
     new("@start",SqlDbType.DateTime){Value=Start},
     new("@end",SqlDbType.DateTime){Value=End}
   };
   return db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args.ToArray()).Tables[0];
 }
 static string Redact(string original){
   if(string.IsNullOrWhiteSpace(original))return "";
   string s=Regex.Replace(original,@"<[^>]+>"," ",RegexOptions.Singleline);
   s=Regex.Replace(s,@"[\p{Cc}\p{Cf}]+"," ");
   s=Regex.Replace(s,@"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b","[CORREO]");
   s=Regex.Replace(s,@"(?i)\b(?:https?://|www\.)\S+","[ENLACE]");
   s=Regex.Replace(s,@"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)","[IP]");
   s=Regex.Replace(s,@"(?i)\b(?:dni|ruc|celular|telefono|teléfono|movil|móvil|contacto|usuario|correo)\s*[:=]\s*\S+(?:\s+\S+)?","[IDENTIFICADOR]");
   s=Regex.Replace(s,@"(?<!\d)\d{6,}(?!\d)","[NUMERO]");
   s=Regex.Replace(s,@"\s+"," ").Trim();
   return s.Length>2200?s[..2200]:s;
 }
 static int Main(){
  try {
    Directory.CreateDirectory(Root);
    foreach(string k in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
      if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(k))){
       string? v=Environment.GetEnvironmentVariable(k,EnvironmentVariableTarget.Machine);
       Require(!string.IsNullOrWhiteSpace(v),"QA_PROVIDER_CONFIG_MISSING");
       Environment.SetEnvironmentVariable(k,v);
      }
    }
    var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
    string cs=xml.Descendants("connectionStrings").Descendants("add")
      .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
      .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
      ??throw new Exception("QA_PROVIDER_CONFIG_ABSENT");
    Require(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)&&
      cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"QA_WRONG_HOST");
    using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
    var db=provider.Obtener(eSistema.ITIL,(byte)1);
    Require(db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
       && db.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase),
       "QA_ITIL_ROUTING_DIFFERENT");
    const string sql=@"SELECT TOP (100)
       CodigoIncidente, FechaSolicitud, CodigoEmpresa, CodigoServicio,
       CodigoModulo, CodigoCalificacion, CodigoOrigenIncidente,
       CodigoEstadoIncidente, DescripcionSolicitud
       FROM dbo.taIncidente
       WHERE FechaSolicitud >= @start AND FechaSolicitud < @end
       ORDER BY FechaSolicitud ASC,CodigoIncidente ASC";
    const string countSql=@"SELECT COUNT_BIG(*) AS total
       FROM dbo.taIncidente
       WHERE FechaSolicitud >= @start AND FechaSolicitud < @end";
    var rows=Q(db,sql,Array.Empty<SqlParameter>());
    var counts=Q(db,countSql,Array.Empty<SqlParameter>());
    Require(rows.Rows.Count==100&&counts.Rows.Count==1,"QA_MAY_COHORT_NOT_HUNDRED");
    long total=Convert.ToInt64(counts.Rows[0]["total"],CultureInfo.InvariantCulture);
    Require(total>=100,"MAY_QA_COHORT_TOO_SMALL");
    string previousDate="";long previousCode=-1;
    var data=new List<object>();
    var chosenHashes=new List<string>();
    var caseSet=new HashSet<string>();
    int nonempty=0;int redactionCandidates=0;
    for(int i=0;i<rows.Rows.Count;i++) {
      var row=rows.Rows[i];
      long id=Convert.ToInt64(row["CodigoIncidente"],CultureInfo.InvariantCulture);
      var date=(DateTime)row["FechaSolicitud"];
      Require(date>=Start&&date<End&&id>0,"QA_OUT_OF_MAY_OR_BAD_ID");
      string dt=date.ToString("yyyy-MM-ddTHH:mm:ss",CultureInfo.InvariantCulture);
      Require(string.CompareOrdinal(dt,previousDate)>0 ||
              (dt==previousDate&&id>previousCode),
              "QA_ORDER_BY_DATE_INCIDENT_ID_DRIFT");
      previousDate=dt;previousCode=id;
      string caseSha=Sha(id.ToString(CultureInfo.InvariantCulture));
      Require(caseSet.Add(caseSha),"QA_DUPLICATE_INCIDENT");
      chosenHashes.Add(caseSha);
      string description=Val(row,"DescripcionSolicitud");
      string redacted=Redact(description);
      if(redacted.Length>0)nonempty++;
      if(description!=redacted)redactionCandidates++;
      data.Add(new{
        rank=i+1,case_sha256=caseSha,opened_at=dt,
        company=Val(row,"CodigoEmpresa"),service_code=Val(row,"CodigoServicio").TrimEnd(),
        module_code=Val(row,"CodigoModulo").TrimEnd(),
        classification_code=Val(row,"CodigoCalificacion"),
        origin_code=Val(row,"CodigoOrigenIncidente"),
        status_code=Val(row,"CodigoEstadoIncidente"),
        description_redacted=redacted,
        description_sha256=Sha(description),
        description_bytes=Encoding.UTF8.GetByteCount(description),
        historical_solution_not_read=true,
        read_only=true
      });
    }
    var receipt=new{
      schema=Schema,worker="ELSE62",qa_server="ELSE70",
      query_id="MAY2026_FIRST100_BY_FECHA_SOLICITUD_AND_CODIGO_INCIDENTE",
      source="dbITIL_D/dbo.taIncidente",start="2026-05-01",
      end_exclusive="2026-06-01",
      ordering="FechaSolicitud_ASC_CodigoIncidente_ASC",
      month_records=total,selected=100,nonempty_descriptions=nonempty,
      descriptions_redacted=redactionCandidates,
      source_sha256=Hash(File.ReadAllBytes(Path.Combine(Root,"MayFirst100Read.cs"))),
      results=data,sql_executed=true,read_only=true,
      business_modifications=0,history_or_resolution_read=false,
      read_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture)
    };
    var bytes=JsonSerializer.SerializeToUtf8Bytes(receipt);
    string path=Path.Combine(Root,"may_first100.private.json");
    File.WriteAllBytes(path,bytes);
    string bodySha=Hash(bytes);
    byte[] key=File.ReadAllBytes(Signer);
    Require(key.Length==32,"QA_HMAC_KEY_WRONG_SIZE");
    string mac=Convert.ToHexString(HMACSHA256.HashData(key,Encoding.UTF8.GetBytes(
       Schema+":"+receipt.source_sha256+":"+bodySha))).ToLowerInvariant();
    var proof=new{
      schema=ProofSchema,worker="ELSE62",source_sha256=receipt.source_sha256,
      receipt_sha256=bodySha,hmac_sha256=mac,read_only=true,
      signed_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture)
    };
    File.WriteAllBytes(path+".proof.json",JsonSerializer.SerializeToUtf8Bytes(proof));
    // Gold/solution SQL is a SEPARATE query executed after the blinded receipt
    // has been serialized. The May model runner reads ONLY may_first100.private.json.
    const string goldSql=@"SELECT TOP (100) CodigoIncidente,
         DescripcionSolucion, FechaRespuestaSolucion, FechaCierre
         FROM dbo.taIncidente
         WHERE FechaSolicitud >= @start AND FechaSolicitud < @end
         ORDER BY FechaSolicitud ASC,CodigoIncidente ASC";
    var historical=Q(db,goldSql,Array.Empty<SqlParameter>());
    Require(historical.Rows.Count==100,"HISTORICAL_QA_HUNDRED_NOT_FOUND");
    var historicalRecords=new List<object>();
    int historicalNonempty=0, historicalWithAnswerDate=0, historicalWithClose=0;
    for(int i=0;i<100;i++){
        var record=historical.Rows[i];
        string keySha=Sha(Val(record,"CodigoIncidente"));
        Require(keySha==chosenHashes[i],"BLIND_GOLD_ALIGNMENT_MISMATCH");
        string original=Val(record,"DescripcionSolucion");
        string redactedSolution=Redact(original);
        if(!string.IsNullOrWhiteSpace(redactedSolution))historicalNonempty++;
        bool answerDate=!record.IsNull("FechaRespuestaSolucion");
        bool closeDate=!record.IsNull("FechaCierre");
        if(answerDate)historicalWithAnswerDate++;
        if(closeDate)historicalWithClose++;
        historicalRecords.Add(new{
           rank=i+1,case_sha256=keySha,
           historical_solution_redacted=redactedSolution,
           historical_solution_sha256=Sha(original),
           historical_solution_original_bytes=Encoding.UTF8.GetByteCount(original),
           answer_date_present=answerDate,close_date_present=closeDate
        });
    }
    var goldReceipt=new {
       schema="else.itil.qa.may2026-first100-history-gold.v1",
       worker="ELSE62",qa_server="ELSE70",
       cohort_source_sha256=bodySha,
       source_sha256=receipt.source_sha256,
       historical_count=100,historical_nonempty=historicalNonempty,
       answer_date_present=historicalWithAnswerDate,
       close_date_present=historicalWithClose,
       solutions_not_in_model_input=true,
       historical_records=historicalRecords,read_only=true,modifications=0,
       read_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture)
    };
    byte[] goldBytes=JsonSerializer.SerializeToUtf8Bytes(goldReceipt);
    string goldPath=Path.Combine(Root,"may_first100_history.private.json");
    File.WriteAllBytes(goldPath,goldBytes);
    string goldSha=Hash(goldBytes);
    string goldMac=Convert.ToHexString(HMACSHA256.HashData(
       key,Encoding.UTF8.GetBytes(goldReceipt.schema+":"+goldReceipt.source_sha256+":"+goldSha)
    )).ToLowerInvariant();
    File.WriteAllBytes(goldPath+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
       schema="else.itil.qa.may2026-first100-history-hmac.v1",
       worker="ELSE62",source_sha256=goldReceipt.source_sha256,
       receipt_sha256=goldSha,hmac_sha256=goldMac,read_only=true
    }));
    Console.WriteLine(JsonSerializer.Serialize(new{
       historical_count=100,historical_nonempty=historicalNonempty,
       with_answer_date=historicalWithAnswerDate,with_close=historicalWithClose,
       history_receipt_sha256=goldSha,model_blind_separate=true
    }));
    Console.WriteLine(JsonSerializer.Serialize(new{
      status="QA_MAY_FIRST100_SQL_PASS",month_records=total,selected=100,
      nonempty_descriptions=nonempty,descriptions_redacted=redactionCandidates,
      window_start=receipt.start,window_end_exclusive=receipt.end_exclusive,
      receipt_sha256=bodySha,reader_sha256=receipt.source_sha256,
      modifications=0,hmac_signed=true
    }));
    return 0;
  }catch(Exception e){
    Console.Error.WriteLine("QA_MAY_FIRST100_FAILED:"+e.GetType().Name);
    return 3;
  }
 }
}
