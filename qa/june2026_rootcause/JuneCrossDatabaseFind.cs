using System;
using System.Data;
using System.Data.SqlClient;
using System.Globalization;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Text;
using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;
using SIELSEAccesoDatos;

// Safe, allowlisted read-only QA diagnosis of the June5 cases.
// All identifiers come from the previously signed private QA receipt.
// No SQL from historical notes, no unbounded scans, no business mutation.
internal static class JuneCrossDatabaseFind {
 const string Root=@"C:\Temp\ELSE_ITIL_JUNE_ROOTCAUSE_20261112";
 const string Old=@"C:\Temp\ELSE_ITIL_JUNE_BUSINESS2026_QA_20261112";
 const string KeyFile=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.2026-june5-crossdb-targets.v1";
 const string HmacSchema="else.itil.qa.2026-june5-crossdb-targets-hmac.v1";
 static readonly string[] AllowDb={
 "dbComercial001_D","dbComercial003_D","dbComercial004_D","dbComercial006_D",
 "dbComercial007_D","dbComercial008_D","dbComercial100_D","dbComercial200_D",
 "dbComercial001_Diario","dbComercial001_20230131","dbComercial003_mayo",
 "dbGerencial_D","dbDistribucion_D"
 };
 static string Hash(byte[] raw)=>Convert.ToHexString(SHA256.HashData(raw)).ToLowerInvariant();
 static void Need(bool ok,string name){if(!ok)throw new Exception(name);}
 static string Val(DataRow row,string col)=>row.IsNull(col)?"":Convert.ToString(row[col],CultureInfo.InvariantCulture)??"";
 static DataTable Q(AccesoDatos db,string stmt, string signature="",SqlParameter? param=null) {
   var args=new List<SqlParameter>{
    new("@stmt",SqlDbType.NVarChar,-1){Value=stmt},
    new("@params",SqlDbType.NVarChar,100){Value=signature}
   };
   if(param!=null)args.Add(param);
   var ds=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args.ToArray());
   Need(ds!=null&&ds.Tables.Count>0,"CROSSDB_EMPTY_RESULT");
   return ds!.Tables[0];
 }
 static void Main(){
  Directory.CreateDirectory(Root);
  foreach(var k in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
   if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(k))){
     string? v=Environment.GetEnvironmentVariable(k,EnvironmentVariableTarget.Machine);
     Need(!string.IsNullOrWhiteSpace(v),"CROSSDB_CORP_CONFIG_NOT_FOUND");
     Environment.SetEnvironmentVariable(k,v);
   }
  }
  byte[] key=File.ReadAllBytes(KeyFile);Need(key.Length==32,"CROSSDB_HMAC_KEY_INVALID");
  var origin=Path.Combine(Old,"june5_exact_business.private.json");
  byte[] receiptRaw=File.ReadAllBytes(origin);
  using var olddoc=JsonDocument.Parse(receiptRaw);
  var old=olddoc.RootElement;
  using var pr=JsonDocument.Parse(File.ReadAllBytes(origin+".proof.json"));
  var proof=pr.RootElement;
  string oldSha=Hash(receiptRaw);
  string sourceSha=old.GetProperty("source_sha256").GetString()??"";
  string oldMac=Convert.ToHexString(HMACSHA256.HashData(key,
    Encoding.UTF8.GetBytes(old.GetProperty("schema").GetString()+":"+sourceSha+":"+oldSha))).ToLowerInvariant();
  Need(proof.GetProperty("receipt_sha256").GetString()==oldSha
    &&proof.GetProperty("source_sha256").GetString()==sourceSha
    &&proof.GetProperty("hmac_sha256").GetString()==oldMac
    &&old.GetProperty("selected").GetInt32()==5,"CROSSDB_JUNE5_SOURCE_NOT_VERIFIED");
  int[] ranks={197,263,868,934,1065};
  var signed=old.GetProperty("rows").EnumerateArray().ToArray();
  Need(signed.Length==5&&signed.Select(x=>x.GetProperty("rank").GetInt32()).SequenceEqual(ranks),
    "CROSSDB_WRONG_CASES");
  var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
  string root=xml.Descendants("connectionStrings").Descendants("add")
   .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
   .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
   ??throw new Exception("CROSSDB_ROOT_MISSING");
  Need(root.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)&&root.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"QA_ROOT_WRONG");
  using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(root));
  AccesoDatos db=provider.Obtener(eSistema.Comercial,(byte)1);
  Need(db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)&&
      db.cdnConexion.NombreBaseDatos.Equals("dbComercial001_D",StringComparison.OrdinalIgnoreCase),
      "CROSSDB_NOT_CORPORATE_QA");
  var dbs=Q(db,@"SELECT name,state_desc
  FROM sys.databases
  WHERE name IN (
  'dbComercial001_D','dbComercial003_D','dbComercial004_D','dbComercial006_D',
  'dbComercial007_D','dbComercial008_D','dbComercial100_D','dbComercial200_D',
  'dbComercial001_Diario','dbComercial001_20230131','dbComercial003_mayo',
  'dbGerencial_D','dbDistribucion_D') ORDER BY name");
  var available=new HashSet<string>(dbs.Rows.Cast<DataRow>()
   .Where(r=>Val(r,"state_desc")=="ONLINE").Select(r=>Val(r,"name")),StringComparer.Ordinal);
  var all=new List<object>();
  int totalPositiveRows=0;
  var distinctMatchedCaseRanks=new HashSet<int>();
  var histogram=new List<object>();
  var errors=new List<object>();
  foreach(string database in AllowDb){
    if(!available.Contains(database)){
      all.Add(new{db=database,metadata="DATABASE_NOT_VISIBLE_ONLINE",tables=new Dictionary<string,bool>(),
           rows=Array.Empty<object>()});continue;
    }
    var tables=new Dictionary<string,bool>(StringComparer.Ordinal);
    try {
      var meta=Q(db,$@"SELECT t.name AS table_name FROM [{database}].sys.tables t
         JOIN [{database}].sys.schemas s ON s.schema_id=t.schema_id
         WHERE s.name='dbo' AND t.name IN
          ('taOrdenTrabajo','taCampanaSupervision','taPadronRuc',
           'taOrdenTrabajoAuditoriaCambio','taOrdenTrabajo_ModificacionIN')");
      foreach(var t in new[]{"taOrdenTrabajo","taCampanaSupervision","taPadronRuc",
        "taOrdenTrabajoAuditoriaCambio","taOrdenTrabajo_ModificacionIN"})
        tables[t]=meta.Rows.Cast<DataRow>().Any(r=>Val(r,"table_name")==t);
    } catch(Exception e){
       errors.Add(new{db=database,operation="METADATA",error_type=e.GetType().Name});
       all.Add(new{db=database,metadata="ACCESS_DENIED_OR_UNAVAILABLE",tables,
          rows=Array.Empty<object>()});continue;
    }
    var results=new List<object>();
    foreach(var x in signed){
       int rank=x.GetProperty("rank").GetInt32();
       string kind=x.GetProperty("kind").GetString()??"";
       string id=x.GetProperty("identifier_private").GetString()??"";
       string table=kind=="PADRON"?"taPadronRuc":kind=="CAMPAIGN"?"taCampanaSupervision":"taOrdenTrabajo";
       if(id.Length==0 || !tables[table]){
          results.Add(new{rank,kind,queried=false,count=-1});continue;
       }
       Need(System.Text.RegularExpressions.Regex.IsMatch(id,@"^\d{8,19}$"),
         "CROSSDB_IDENTIFIER_NOT_NUMERIC");
       string keycol=kind=="PADRON"?"NumeroDNI":kind=="CAMPAIGN"?"CodigoCampanaSupervision":"CodigoOrdenTrabajo";
       try {
          string sql=$"SELECT COUNT_BIG(*) AS n FROM [{database}].dbo.{table} WHERE {keycol}=@value";
          var t=kind=="PADRON"?new SqlParameter("@value",SqlDbType.VarChar,12){Value=id}:
               new SqlParameter("@value",SqlDbType.BigInt){Value=long.Parse(id,CultureInfo.InvariantCulture)};
          var matched=Q(db,sql,kind=="PADRON"?"@value varchar(12)":"@value bigint",t);
          long n=Convert.ToInt64(matched.Rows[0]["n"],CultureInfo.InvariantCulture);
          if(n>0){totalPositiveRows+=checked((int)n);distinctMatchedCaseRanks.Add(rank);}
          results.Add(new{rank,kind,queried=true,count=n});
       }catch(Exception e){
          errors.Add(new{db=database,rank,operation="EXACT_ID",error_type=e.GetType().Name});
          results.Add(new{rank,kind,queried=false,count=-2});
       }
    }
    if(tables["taOrdenTrabajo"]){
      try {
        // Nonidentifying distribution from at most 200 rows.
        var h=Q(db,$@"SELECT code_length,COUNT_BIG(*) AS n FROM
         (SELECT TOP(200) LEN(CONVERT(varchar(32),CodigoOrdenTrabajo)) AS code_length
          FROM [{database}].dbo.taOrdenTrabajo) R
          GROUP BY code_length ORDER BY code_length");
        foreach(DataRow r in h.Rows)histogram.Add(new{db=database,
          len=Convert.ToInt32(r["code_length"]),count=Convert.ToInt64(r["n"])});
      }catch(Exception e){errors.Add(new{db=database,operation="LENGTH_SAMPLE",error_type=e.GetType().Name});}
    }
    all.Add(new{db=database,metadata="VISIBLE",tables,rows=results});
  }
  string codeHash=Hash(File.ReadAllBytes(Path.Combine(Root,"JuneCrossDatabaseFind.cs")));
  var output=new{schema=Schema,source_sha256=codeHash,worker="ELSE62",
    qa_server="ELSE70",qa_start="dbComercial001_D",
    june5_signed_source_receipt_sha256=oldSha,
    searched_databases=all,
    identifier_length_histograms_sample200=histogram,
    errors,allowed_db_names=AllowDb,
    no_ids_exported_in_result=true,
    no_historical_sql_executed=true,
    read_only=true,business_modifications=0};
  byte[] raw=JsonSerializer.SerializeToUtf8Bytes(output);
  string digest=Hash(raw);
  string mac=Convert.ToHexString(HMACSHA256.HashData(key,
     Encoding.UTF8.GetBytes(Schema+":"+codeHash+":"+digest))).ToLowerInvariant();
  string dst=Path.Combine(Root,"june5_crossdb.private.json");
  File.WriteAllBytes(dst,raw);
  File.WriteAllBytes(dst+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
    schema=HmacSchema,source_sha256=codeHash,receipt_sha256=digest,
    hmac_sha256=mac,read_only=true
  }));
  Console.WriteLine(JsonSerializer.Serialize(new{
    status="CROSS_DATABASE_QA_COMPLETED",
    databases_visible=all.Count,positive_rows_across_db=totalPositiveRows,distinct_matched_cases=distinctMatchedCaseRanks.Count,error_count=errors.Count,
    receipt_sha256=digest,code_sha256=codeHash
  }));
 }
}
