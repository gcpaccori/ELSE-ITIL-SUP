using System;
using System.Data;
using System.Data.SqlClient;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.IO;
using System.Text.Json;
using System.Xml.Linq;
using SIELSEAccesoDatos;

// Schema-only fixed SELECT for 3 business tables + candidate immutable audit
// tables. No business values, passwords, or arbitrary SQL from tickets.
internal static class JuneBusinessMetaRead {
 static void Need(bool b,string msg){if(!b) throw new Exception(msg);}
 static DataTable Q(AccesoDatos db,string sql) {
  var set=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",new SqlParameter[]{
   new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
   new("@params",SqlDbType.NVarChar,20){Value=""}
  });
  Need(set!=null&&set.Tables.Count>0,"METADATA_NO_ROWS_DATASET");
  return set!.Tables[0];
 }
 static void Main(){
  foreach(string k in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}) {
   if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(k))){
    var v=Environment.GetEnvironmentVariable(k,EnvironmentVariableTarget.Machine);
    Need(!string.IsNullOrWhiteSpace(v),"METADATA_QA_CONFIG_MISSING");
    Environment.SetEnvironmentVariable(k,v);
   }
  }
  var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
  var cs=xml.Descendants("connectionStrings").Descendants("add")
   .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
   .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault();
  Need(cs!=null&&cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)
      &&cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"METADATA_ROOT_INVALID");
  using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
  var db=provider.Obtener(eSistema.Comercial,(byte)1);
  Need(db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
    &&db.cdnConexion.NombreBaseDatos.Equals("dbComercial001_D",StringComparison.OrdinalIgnoreCase),
    "METADATA_UNAUTHORIZED_DESTINATION");
  const string columnSql=@"
SELECT t.name AS table_name,c.name AS column_name,
       ty.name AS data_type,c.max_length,c.is_nullable
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id=t.schema_id
JOIN sys.columns c ON c.object_id=t.object_id
JOIN sys.types ty ON ty.user_type_id=c.user_type_id
WHERE s.name='dbo' AND t.name IN
 ('taOrdenTrabajo','taOrdenTrabajoAuditoriaCambio',
  'taOrdenTrabajo_ModificacionIN','taOrdenTrabajoEstadoHistorico',
  'taCampanaSupervision','taPadronRuc')
ORDER BY t.name,c.column_id";
  const string timeSql=@"
SELECT t.name AS table_name,t.temporal_type_desc,
  ht.name AS history_table,COUNT(tr.object_id) AS trigger_count
FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
LEFT JOIN sys.tables ht ON ht.object_id=t.history_table_id
LEFT JOIN sys.triggers tr ON tr.parent_id=t.object_id
WHERE s.name='dbo' AND t.name IN
 ('taOrdenTrabajo','taOrdenTrabajoAuditoriaCambio',
  'taOrdenTrabajo_ModificacionIN','taOrdenTrabajoEstadoHistorico',
  'taCampanaSupervision','taPadronRuc')
GROUP BY t.name,t.temporal_type_desc,ht.name ORDER BY t.name";
  const string auditSql=@"
SELECT TOP(60) t.name AS table_name
FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
WHERE s.name='dbo' AND (
 t.name LIKE '%Campana%Auditor%' OR t.name LIKE '%Campana%Histor%'
 OR t.name LIKE '%Padron%Auditor%' OR t.name LIKE '%Padron%Histor%'
 OR t.name LIKE '%OrdenTrabajo%Auditor%'
 OR t.name LIKE '%OrdenTrabajo%Histor%'
 OR t.name LIKE '%OrdenTrabajo%Modifica%')
ORDER BY t.name";
  var cols=Q(db,columnSql).Rows.Cast<DataRow>().Select(x=>new{
   table=Convert.ToString(x["table_name"]),column=Convert.ToString(x["column_name"]),
   type=Convert.ToString(x["data_type"])}).ToArray();
  var temporal=Q(db,timeSql).Rows.Cast<DataRow>().Select(x=>new{
    table=Convert.ToString(x["table_name"]),temporal=Convert.ToString(x["temporal_type_desc"]),
    history=Convert.ToString(x["history_table"]),triggers=Convert.ToInt32(x["trigger_count"])}).ToArray();
  var audit=Q(db,auditSql).Rows.Cast<DataRow>().Select(x=>Convert.ToString(x["table_name"])).ToArray();
  const string path=@"C:\Temp\ELSE_ITIL_JUNE_BUSINESS2026_QA_20261112";
  const string schema="else.itil.qa.2026-june5-business-metadata.v1";
  const string proofSchema="else.itil.qa.2026-june5-business-metadata-hmac.v1";
  const string src=@"C:\Temp\ELSE_ITIL_JUNE_BUSINESS2026_QA_20261112\JuneBusinessMetaRead.cs";
  const string signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
  var codeHash=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(src))).ToLowerInvariant();
  var output=new {schema,source_sha256=codeHash,qa="ELSE70/dbComercial001_D",
    columns=cols,temporal=temporal,candidate_history_tables=audit,
    read_only=true,modifications=0};
  byte[] raw=JsonSerializer.SerializeToUtf8Bytes(output);
  var digest=Convert.ToHexString(SHA256.HashData(raw)).ToLowerInvariant();
  byte[] key=File.ReadAllBytes(signer);
  Need(key.Length==32,"QA_META_HMAC_INVALID");
  var mac=Convert.ToHexString(HMACSHA256.HashData(key,
    Encoding.UTF8.GetBytes(schema+":"+codeHash+":"+digest))).ToLowerInvariant();
  File.WriteAllBytes(Path.Combine(path,"june5_metadata.private.json"),raw);
  File.WriteAllBytes(Path.Combine(path,"june5_metadata.private.json.proof.json"),
    JsonSerializer.SerializeToUtf8Bytes(new {schema=proofSchema,worker="ELSE62",
      source_sha256=codeHash,receipt_sha256=digest,hmac_sha256=mac,read_only=true}));
  Console.WriteLine(JsonSerializer.Serialize(new {schema,code_sha256=codeHash,
    receipt_sha256=digest,tables=temporal.Length,candidate_history_tables=audit.Length,
    columns=cols.Length,read_only=true}));
 }
}
