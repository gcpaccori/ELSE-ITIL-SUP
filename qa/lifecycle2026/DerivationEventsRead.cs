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

// Second independent read: the actual taIncidenteDerivacion rows for the 900
// signed incidents, matched by CodigoIncidente exact equality. No user names,
// explanations, comments, original incident IDs, or modification privileges.
internal static class DerivationEventsRead {
 const string Root=@"C:\Temp\ELSE_ITIL_WORKFLOW_QA_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.2026-native-derivation-events.v1";
 const string SourceSchema="else.itil.qa.2026-case-lifecycle-native-keys.v1";
 static string Hash(byte[] d)=>Convert.ToHexString(SHA256.HashData(d)).ToLowerInvariant();
 static string Sha(string s)=>Hash(Encoding.UTF8.GetBytes(s));
 static void Need(bool ok,string code){if(!ok)throw new Exception(code);}
 static string Val(DataRow r,string col)=>r.IsNull(col)?"":Convert.ToString(r[col],CultureInfo.InvariantCulture)??"";
 static string Mac(string schema,string src,string receipt,byte[] key)=>
   Convert.ToHexString(HMACSHA256.HashData(key,Encoding.UTF8.GetBytes(schema+":"+src+":"+receipt))).ToLowerInvariant();
 const string Query=@"WITH C AS (
    SELECT TOP (100) CodigoIncidente
    FROM dbo.taIncidente
    WHERE FechaSolicitud>=@start AND FechaSolicitud<@end
    ORDER BY FechaSolicitud DESC,CodigoIncidente DESC
   )
   SELECT d.CodigoIncidente,d.NumeroDerivacion,
          d.CodigoTipoDerivacionIncidente,d.FechaCreacion,d.FechaModificacion
   FROM C JOIN dbo.taIncidenteDerivacion d ON d.CodigoIncidente=C.CodigoIncidente
   ORDER BY d.CodigoIncidente,d.NumeroDerivacion";
 static DataTable Q(AccesoDatos db,DateTime start,DateTime end){
   var data=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",
     new SqlParameter[]{
       new("@stmt",SqlDbType.NVarChar,-1){Value=Query},
       new("@params",SqlDbType.NVarChar,80){Value="@start datetime,@end datetime"},
       new("@start",SqlDbType.DateTime){Value=start},
       new("@end",SqlDbType.DateTime){Value=end}
     });
   Need(data!=null&&data.Tables.Count>0,"QA_QUERY_NO_TABLE");
   return data!.Tables[0];
 }
 static int Main(){
  try{
   Directory.CreateDirectory(Root);
   foreach(var env in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
     if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(env))){
       var v=Environment.GetEnvironmentVariable(env,EnvironmentVariableTarget.Machine);
       Need(!string.IsNullOrWhiteSpace(v),"QA_CONNECTOR_KEY_MISSING");
       Environment.SetEnvironmentVariable(env,v);
     }
   }
   var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string cs=xml.Descendants("connectionStrings").Descendants("add")
       .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
       .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
       ??throw new Exception("QA_CONFIG_NOT_FOUND");
   Need(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase) &&
        cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"QA_BAD_ROOT");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
   var db=provider.Obtener(eSistema.ITIL,(byte)1);
   Need(db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
        && db.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase),
        "QA_WRONG_DATABASE");
   byte[] key=File.ReadAllBytes(Signer);
   Need(key.Length==32,"QA_SIGNER_BAD");
   string readerSource=Hash(File.ReadAllBytes(Path.Combine(Root,"CaseLifecycleRead.cs")));
   byte[] sourceBytes=File.ReadAllBytes(Path.Combine(Root,"itil_native_lifecycle_900.private.json"));
   var source=JsonDocument.Parse(sourceBytes);
   var proof=JsonDocument.Parse(File.ReadAllBytes(Path.Combine(Root,"itil_native_lifecycle_900.private.json.proof.json")));
   string sourceReceipt=Hash(sourceBytes);
   var d=source.RootElement;var sp=proof.RootElement;
   Need(d.GetProperty("schema").GetString()==SourceSchema &&
       d.GetProperty("source_sha256").GetString()==readerSource &&
       sp.GetProperty("receipt_sha256").GetString()==sourceReceipt &&
       sp.GetProperty("source_sha256").GetString()==readerSource &&
       Mac(SourceSchema,readerSource,sourceReceipt,key)==sp.GetProperty("hmac_sha256").GetString() &&
       d.GetProperty("selected").GetInt32()==900 &&
       d.GetProperty("read_only").GetBoolean() &&
       d.GetProperty("results").GetArrayLength()==900,
       "SOURCE_CASE_LIFECYCLE_RECEIPT_UNVERIFIED");
   var known=new Dictionary<string,(string Month,int Rank,int Count)>(StringComparer.Ordinal);
   foreach(var row in d.GetProperty("results").EnumerateArray()){
      string hash=row.GetProperty("case_sha256").GetString()??"";
      Need(hash.Length==64&&!known.ContainsKey(hash),"SOURCE_DUPLICATE_CASE");
      known[hash]=(row.GetProperty("month").GetString()??"",
                   row.GetProperty("rank").GetInt32(),
                   row.GetProperty("exact_key_equality_derivacion").GetInt32());
   }
   Need(known.Count==900,"SOURCE_NOT_900");
   var seen=new HashSet<string>(StringComparer.Ordinal);
   var counts=new Dictionary<string,int>(StringComparer.Ordinal);
   var events=new List<object>();
   var monthly=new List<object>();
   int dated=0;
   for(int month=1;month<=9;month++){
      var start=new DateTime(2026,month,1);
      var end=start.AddMonths(1);
      string ym="2026-"+month.ToString("00",CultureInfo.InvariantCulture);
      var rows=Q(db,start,end);
      monthly.Add(new{month=ym,events_returned=rows.Rows.Count});
      foreach(DataRow row in rows.Rows){
         string caseHash=Sha(Val(row,"CodigoIncidente"));
         int number=Convert.ToInt32(row["NumeroDerivacion"],CultureInfo.InvariantCulture);
         string type=Val(row,"CodigoTipoDerivacionIncidente");
         string unique=caseHash+":"+number.ToString(CultureInfo.InvariantCulture);
         Need(known.ContainsKey(caseHash) && known[caseHash].Month==ym &&
              number>=0&&number<=32767 && seen.Add(unique) && type.Length<=20,
              "DERIVATION_EVENT_COHORT_OR_PK_DRIFT");
         if(!counts.ContainsKey(caseHash))counts[caseHash]=0;
         counts[caseHash]++;
         string created=row.IsNull("FechaCreacion")?"":((DateTime)row["FechaCreacion"]).ToString("yyyy-MM-ddTHH:mm:ss",CultureInfo.InvariantCulture);
         bool modified=!row.IsNull("FechaModificacion");
         if(created.Length>0)dated++;
         events.Add(new{
           month=ym,rank=known[caseHash].Rank,
           case_sha256=caseHash,
           numero_derivacion=number,
           codigo_tipo_derivacion=type,
           fecha_creacion_utc_unspecified_local=created,
           fecha_modificacion_present=modified,
           exact_same_codigo_incidente_as_ticket=true,
           official_sql_fk_declared=false,
           historical_business_fix_executed_certified=false
         });
      }
   }
   Need(events.Count==d.GetProperty("derivation_rows").GetInt32(),"DERIVATION_TOTAL_DRIFT");
   foreach(var item in known){
      int actual=counts.GetValueOrDefault(item.Key,0);
      Need(actual==item.Value.Count,"DERIVATION_PER_CASE_REBOUND");
   }
   string ownSha=Hash(File.ReadAllBytes(Path.Combine(Root,"DerivationEventsRead.cs")));
   var receipt=new{
      schema=Schema,source_sha256=ownSha,worker="ELSE62",
      qa_server="ELSE70",qa_database="dbITIL_D",
      origin="dbo.taIncidenteDerivacion",
      parent_source="dbo.taIncidente",
      source_lifecycle_receipt_sha256=sourceReceipt,
      selected_tickets=900,
      events_count=events.Count,
      events_with_creation_date=dated,
      months=monthly,
      results=events,
      relationship="OBSERVED_EXACT_CODIGO_INCIDENTE_KEY_EQUALITY_NOT_FOREIGN_KEY",
      formal_itil_to_derivacion_foreign_key_verified=false,
      modifications=0,causal_fixes_certified=0,read_only=true,
      read_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture)
   };
   byte[] body=JsonSerializer.SerializeToUtf8Bytes(receipt);
   string file=Path.Combine(Root,"itil_derivation_events_900.private.json");
   File.WriteAllBytes(file,body);
   string hashBody=Hash(body);
   File.WriteAllBytes(file+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
      schema="else.itil.qa.2026-native-derivation-events-hmac.v1",
      source_sha256=ownSha,receipt_sha256=hashBody,
      hmac_sha256=Mac(Schema,ownSha,hashBody,key),read_only=true,worker="ELSE62"
   }));
   Console.WriteLine(JsonSerializer.Serialize(new{
       status="DERIVATION_EVENTS_SIGNED",
       case_count=known.Count,events=events.Count,
       events_with_creation_date=dated,
       formal_fk_certified=false,
       repairs_certified=0,
       receipt_sha256=hashBody
   }));
   return 0;
  }catch(Exception ex){
   Console.Error.WriteLine("DERIVATION_EVENTS_FAILED:"+ex.GetType().Name+":"+ex.Message);
   return 3;
  }
 }
}
