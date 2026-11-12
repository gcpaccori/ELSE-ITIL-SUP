using System;
using System.Data;
using System.Data.SqlClient;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Xml.Linq;
using SIELSEAccesoDatos;

// Metadata-only search for June 2026 historical recovery prerequisites.
// Does NOT restore a backup, open its files, or read business rows.
internal static class JuneHistoricalAvailabilityRead {
 const string Root=@"C:\Temp\ELSE_ITIL_JUNE_ROOTCAUSE_20261112";
 const string KeyFile=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.2026-historical-availability-metadata.v1";
 const string Proof="else.itil.qa.2026-historical-availability-metadata-hmac.v1";
 static void Need(bool ok,string error){if(!ok)throw new Exception(error);}
 static string Sha(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
 static string Val(DataRow row,string name)=>row.IsNull(name)?"":Convert.ToString(row[name],CultureInfo.InvariantCulture)??"";
 static DataTable Q(AccesoDatos db,string sql) {
   var ds=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",new SqlParameter[]{
     new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
     new("@params",SqlDbType.NVarChar,2){Value=""}
   });
   Need(ds!=null&&ds.Tables.Count>0,"HIST_META_NO_DATASET");
   return ds!.Tables[0];
 }
 static void Main(){
   Directory.CreateDirectory(Root);
   foreach(var k in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
     if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(k))){
       var v=Environment.GetEnvironmentVariable(k,EnvironmentVariableTarget.Machine);
       Need(!string.IsNullOrWhiteSpace(v),"HIST_META_CONFIG_MISSING");
       Environment.SetEnvironmentVariable(k,v);
     }
   }
   var x=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string cs=x.Descendants("connectionStrings").Descendants("add")
      .Where(z=>(string?)z.Attribute("name")=="ConexionSIELSE")
      .Select(z=>(string?)z.Attribute("connectionString")).SingleOrDefault()
      ??throw new Exception("HIST_META_ROOT_MISSING");
   Need(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)
       &&cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"QA_ROOT_INVALID");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
   AccesoDatos db=provider.Obtener(eSistema.Comercial,(byte)1);
   Need(db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
       &&db.cdnConexion.NombreBaseDatos.Equals("dbComercial001_D",StringComparison.OrdinalIgnoreCase),
       "HIST_META_WRONG_SOURCE");
   var states=new List<object>();
   var errors=new List<object>();
   try {
     var t=Q(db,@"SELECT name,is_cdc_enabled,state_desc
       FROM sys.databases
       WHERE name IN ('dbComercial001_D','dbComercial004_D',
        'dbComercial100_D','dbGerencial_D')");
     foreach(DataRow r in t.Rows){
       states.Add(new{db=Val(r,"name"),
        cdc_enabled=Val(r,"is_cdc_enabled")=="True"||Val(r,"is_cdc_enabled")=="1",
        state=Val(r,"state_desc")});
     }
   }catch(Exception e){errors.Add(new{stage="CDC_METADATA",error=e.GetType().Name});}
   var backups=new List<object>();
   try {
     var t=Q(db,@"SELECT database_name,COUNT_BIG(*) AS backup_count,
        MIN(backup_finish_date) AS first_backup,MAX(backup_finish_date) AS last_backup
       FROM msdb.dbo.backupset
       WHERE database_name IN ('dbComercial001_D','dbComercial004_D',
        'dbComercial100_D','dbGerencial_D')
        AND backup_finish_date >= '2026-06-01'
        AND backup_finish_date < '2026-07-01'
       GROUP BY database_name");
     foreach(DataRow r in t.Rows){
       backups.Add(new{
         db=Val(r,"database_name"),
         backup_count=Convert.ToInt64(r["backup_count"],CultureInfo.InvariantCulture),
         earliest=Val(r,"first_backup"),latest=Val(r,"last_backup")});
     }
   } catch(Exception e){errors.Add(new{stage="JUNE_BACKUPSET_ACCESS",error=e.GetType().Name});}
   string sha=Sha(File.ReadAllBytes(Path.Combine(Root,"JuneHistoricalAvailabilityRead.cs")));
   var output=new{schema=Schema,source_sha256=sha,qa_server="ELSE70",
       cdc_metadata=states,backup_metadata=backups,access_errors=errors,
       backup_files_not_opened=true,restores_executed=0,read_only=true,
       business_writes=0};
   byte[] raw=JsonSerializer.SerializeToUtf8Bytes(output);
   string hash=Sha(raw);byte[] key=File.ReadAllBytes(KeyFile);
   Need(key.Length==32,"HIST_META_HMAC_KEY_BAD");
   var mac=Convert.ToHexString(HMACSHA256.HashData(key,
       Encoding.UTF8.GetBytes(Schema+":"+sha+":"+hash))).ToLowerInvariant();
   string path=Path.Combine(Root,"historical_availability.private.json");
   File.WriteAllBytes(path,raw);
   File.WriteAllBytes(path+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
     schema=Proof,source_sha256=sha,receipt_sha256=hash,hmac_sha256=mac,
     read_only=true}));
   Console.WriteLine(JsonSerializer.Serialize(new{
      status="HISTORICAL_METADATA_READ_FINISHED",
      databases=states.Count,backups_in_june_database_groups=backups.Count,
      metadata_errors=errors.Count,
      receipt_sha256=hash,no_restore=true,read_only=true
   }));
 }
}
