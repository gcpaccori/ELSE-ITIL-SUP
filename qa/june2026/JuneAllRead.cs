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

// Read-only QA: ALL June 2026 incidents by FechaSolicitud DESC / CodigoIncidente DESC.
// Full June original request cohort is sealed before any historical solution read.
// June closed month [2026-06-01,2026-07-01).
internal static class JuneAllRead {
 const string Root=@"C:\Temp\ELSE_ITIL_JUNEALL2026_QA_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.2026-juneall-source.v1";
 const string GoldSchema="else.itil.qa.2026-juneall-history.v1";
 static string Hex(byte[] v)=>Convert.ToHexString(SHA256.HashData(v)).ToLowerInvariant();
 static string Sha(string x)=>Hex(Encoding.UTF8.GetBytes(x));
 static string Val(DataRow r,string name)=>r.IsNull(name)?"":Convert.ToString(r[name],CultureInfo.InvariantCulture)??"";
 static void Need(bool value,string code){if(!value)throw new Exception(code);}
 static string Redact(string original) {
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
 static DataTable Q(AccesoDatos db,string sql,DateTime start,DateTime end){
   var args=new SqlParameter[]{
      new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
      new("@params",SqlDbType.NVarChar,80){Value="@start datetime,@end datetime"},
      new("@start",SqlDbType.DateTime){Value=start},
      new("@end",SqlDbType.DateTime){Value=end}
   };
   var set=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args);
   Need(set!=null&&set.Tables.Count>0,"QA_SQL_NO_TABLE");
   return set!.Tables[0];
 }
 static string SignedWrite(string filename,object obj,string sourceSha,string signatureSchema,byte[] key) {
    byte[] bytes=JsonSerializer.SerializeToUtf8Bytes(obj);
    string path=Path.Combine(Root,filename);
    File.WriteAllBytes(path,bytes);
    string hash=Hex(bytes);
    string mac=Convert.ToHexString(HMACSHA256.HashData(key,
       Encoding.UTF8.GetBytes(
           JsonSerializer.SerializeToElement(obj).GetProperty("schema").GetString()
           +":"+sourceSha+":"+hash))).ToLowerInvariant();
    File.WriteAllBytes(path+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new {
        schema=signatureSchema,worker="ELSE62",source_sha256=sourceSha,
        receipt_sha256=hash,hmac_sha256=mac,read_only=true
    }));
    return hash;
 }
 const string CountSql=@"SELECT COUNT_BIG(*) AS total FROM dbo.taIncidente
                        WHERE FechaSolicitud>=@start AND FechaSolicitud<@end";
 const string RequestSql=@"SELECT CodigoIncidente,FechaSolicitud,CodigoEmpresa,
          CodigoServicio,CodigoModulo,CodigoCalificacion,CodigoOrigenIncidente,
          CodigoEstadoIncidente,DescripcionSolicitud
          FROM dbo.taIncidente
          WHERE FechaSolicitud>=@start AND FechaSolicitud<@end
          ORDER BY FechaSolicitud DESC,CodigoIncidente DESC";
 const string HistoricalSql=@"SELECT CodigoIncidente,DescripcionSolucion,
          FechaRespuestaSolucion,FechaCierre
          FROM dbo.taIncidente
          WHERE FechaSolicitud>=@start AND FechaSolicitud<@end
          ORDER BY FechaSolicitud DESC,CodigoIncidente DESC";
 static void OneMonth(AccesoDatos db,byte[] key,string sourceSha,int month) {
    DateTime start=new(2026,month,1);
    DateTime end=start.AddMonths(1);
    string ym=start.ToString("yyyy-MM",CultureInfo.InvariantCulture);
    var summary=Q(db,CountSql,start,end);
    Need(summary.Rows.Count==1,"QA_MONTH_COUNT_MISSING");
    long total=Convert.ToInt64(summary.Rows[0]["total"],CultureInfo.InvariantCulture);
    var rows=Q(db,RequestSql,start,end);
    Need(total>0&&total<100000,"QA_JUNE_UNREASONABLE_COUNT");
    int selected=checked((int)total);
    Need(rows.Rows.Count==selected,"QA_JUNE_ALL_ROWS_MISMATCH");
    string previousDate="";long previousCode=long.MaxValue;
    var keys=new HashSet<string>();
    var sourceRows=new List<object>();
    var keyOrder=new List<string>();
    int nonempty=0,redacted=0;
    for(int i=0;i<selected;i++) {
       DataRow row=rows.Rows[i];
       long id=Convert.ToInt64(row["CodigoIncidente"],CultureInfo.InvariantCulture);
       var date=(DateTime)row["FechaSolicitud"];
       string dt=date.ToString("yyyy-MM-ddTHH:mm:ss",CultureInfo.InvariantCulture);
       Need(id>0&&date>=start&&date<end,"QA_MONTH_COHORT_OUTSIDE_RANGE");
       Need(i==0||string.CompareOrdinal(dt,previousDate)<0||
             (dt==previousDate&&id<previousCode),"QA_MONTH_DESCENDING_ORDER_INVALID");
       previousDate=dt;previousCode=id;
       string caseSha=Sha(id.ToString(CultureInfo.InvariantCulture));
       Need(keys.Add(caseSha),"QA_MONTH_DUPLICATE_INCIDENT");
       keyOrder.Add(caseSha);
       string original=Val(row,"DescripcionSolicitud");
       string clean=Redact(original);
       if(clean.Length>0)nonempty++;
       if(clean!=original)redacted++;
       sourceRows.Add(new {
          rank=i+1,case_sha256=caseSha,opened_at=dt,
          company=Val(row,"CodigoEmpresa"),
          service_code=Val(row,"CodigoServicio").TrimEnd(),
          module_code=Val(row,"CodigoModulo").TrimEnd(),
          classification_code=Val(row,"CodigoCalificacion"),
          origin_code=Val(row,"CodigoOrigenIncidente"),
          status_code=Val(row,"CodigoEstadoIncidente"),
          description_redacted=clean,
          description_sha256=Sha(original),
          historical_solution_not_read=true,read_only=true
       });
    }
    string name="juneall_"+ym.Replace("-","")+".private.json";
    var sourceReceipt=new {
        schema=Schema,worker="ELSE62",qa_server="ELSE70",
        source="dbITIL_D/dbo.taIncidente",
        selection="ALL_JUNE_FECHA_SOLICITUD_DESC_CODIGO_INCIDENTE_DESC",
        period=ym,start=start.ToString("yyyy-MM-dd",CultureInfo.InvariantCulture),
        end_exclusive=end.ToString("yyyy-MM-dd",CultureInfo.InvariantCulture),
        month_closed=true,asof_date="2026-11-12",
        month_records=total,selected,nonempty_descriptions=nonempty,
        redactions_applied=redacted,
        source_sha256=sourceSha,results=sourceRows,
        history_or_resolution_read=false,read_only=true,
        business_modifications=0,
        read_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture)
    };
    string sourceHash=SignedWrite(name,sourceReceipt,sourceSha,
        "else.itil.qa.2026-juneall-source-hmac.v1",key);
    // Strictly later: fetch solutions into a different receipt file.
    var historical=Q(db,HistoricalSql,start,end);
    Need(historical.Rows.Count==selected,"QA_JUNE_ALL_GOLD_COUNT_MISMATCH");
    var historicRows=new List<object>();
    int solutionNonempty=0,hasAnswer=0,hasClose=0;
    for(int i=0;i<selected;i++){
       var row=historical.Rows[i];
       string keySha=Sha(Val(row,"CodigoIncidente"));
       Need(keySha==keyOrder[i],"QA_MONTH_GOLD_BINDING_MISMATCH");
       string original=Val(row,"DescripcionSolucion");
       string cleaned=Redact(original);
       if(!string.IsNullOrWhiteSpace(cleaned))solutionNonempty++;
       bool answer=!row.IsNull("FechaRespuestaSolucion"),closed=!row.IsNull("FechaCierre");
       if(answer)hasAnswer++;
       if(closed)hasClose++;
       historicRows.Add(new {
          rank=i+1,case_sha256=keySha,
          historical_solution_redacted=cleaned,
          historical_solution_sha256=Sha(original),
          answer_date_present=answer,close_date_present=closed
       });
    }
    var goldReceipt=new {
       schema=GoldSchema,worker="ELSE62",qa_server="ELSE70",
       period=ym,source_sha256=sourceSha,
       cohort_source_sha256=sourceHash,historical_count=selected,
       historical_nonempty=solutionNonempty,answer_date_present=hasAnswer,
       close_date_present=hasClose,solutions_not_in_model_input=true,
       historical_records=historicRows,
       business_modifications=0,read_only=true,
       read_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture)
    };
    string goldSha=SignedWrite("juneall_"+ym.Replace("-","")+"_history.private.json",
       goldReceipt,sourceSha,"else.itil.qa.2026-juneall-history-hmac.v1",key);
    Console.WriteLine(JsonSerializer.Serialize(new{
       month=ym,total,selected,month_closed=true,
       first=selected>0?sourceRows[0].GetType().GetProperty("opened_at")?.GetValue(sourceRows[0]):null,
       historical_nonempty=solutionNonempty,
       with_answer_date=hasAnswer,with_close=hasClose,
       source_receipt_sha256=sourceHash,
       history_receipt_sha256=goldSha,read_only=true
    }));
 }
 static int Main(){
   try{
     Directory.CreateDirectory(Root);
     foreach(string k in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
       if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(k))){
         string? v=Environment.GetEnvironmentVariable(k,EnvironmentVariableTarget.Machine);
         Need(!string.IsNullOrWhiteSpace(v),"QA_CONNECTOR_CONFIG_MISSING");
         Environment.SetEnvironmentVariable(k,v);
       }
     }
     var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
     string cs=xml.Descendants("connectionStrings").Descendants("add")
       .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
       .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
       ??throw new Exception("QA_NO_CONNECTOR_ROOT");
     Need(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)&&
        cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"QA_BAD_ROOT");
     using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
     var db=provider.Obtener(eSistema.ITIL,(byte)1);
     Need(db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
       && db.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase),
       "QA_WRONG_DB_ROUTE");
     byte[] key=File.ReadAllBytes(Signer);
     Need(key.Length==32,"QA_SIGNING_KEY_INVALID");
     string sourceSha=Hex(File.ReadAllBytes(Path.Combine(Root,"JuneAllRead.cs")));
     OneMonth(db,key,sourceSha,6);
     Console.WriteLine("JUNE_ALL_2026_QA_COMPLETE");
     return 0;
   }catch(Exception ex){
     Console.Error.WriteLine("JUNE_ALL_2026_FAILED:"+ex.GetType().Name+":"+ex.Message);
     return 3;
   }
 }
}
