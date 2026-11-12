using System;
using System.Data;
using System.Data.SqlClient;
using System.Globalization;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text;
using System.Security.Cryptography;
using System.IO;
using System.Xml.Linq;
using SIELSEAccesoDatos;

// Read-only strict QA reconciliation of June5 objects recovered by earlier
// signed cross-DB target search. NEVER run SQL stored in ITIL notes.
internal static class JuneRecoveredObjectsRead {
 const string Root=@"C:\Temp\ELSE_ITIL_JUNE_ROOTCAUSE_20261112";
 const string FiveRoot=@"C:\Temp\ELSE_ITIL_JUNE_BUSINESS2026_QA_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.2026-june5-recovered-objects-and-audit.v1";
 const string ProofSchema="else.itil.qa.2026-june5-recovered-objects-and-audit-hmac.v1";
 const string CrossSchema="else.itil.qa.2026-june5-crossdb-targets.v1";
 const string FiveSchema="else.itil.qa.2026-june5-exact-business-snapshot.v1";
 const string ReaderName="JuneRecoveredObjectsRead.cs";
 static void Need(bool b,string e){if(!b)throw new Exception(e);}
 static string Hash(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
 static string Hmac(byte[] key,string schema,string source,string data)=>Convert.ToHexString(
   HMACSHA256.HashData(key,Encoding.UTF8.GetBytes(schema+":"+source+":"+data))).ToLowerInvariant();
 static string Val(DataRow r,string c)=>r.IsNull(c)?"":Convert.ToString(r[c],CultureInfo.InvariantCulture)??"";
 static object? Date(DataRow r,string c)=>r.IsNull(c)?null:r[c] is DateTime dt?dt.ToString("O"):Val(r,c);
 static DataTable Q(AccesoDatos db,string stmt,string signature="",SqlParameter? v=null) {
   var args=new List<SqlParameter> {
     new("@stmt",SqlDbType.NVarChar,-1){Value=stmt},
     new("@params",SqlDbType.NVarChar,100){Value=signature}
   };
   if(v!=null)args.Add(v);
   var ds=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args.ToArray());
   Need(ds!=null&&ds.Tables.Count>0,"QA_DATASET_UNAVAILABLE");
   return ds!.Tables[0];
 }
 static (JsonDocument,string) Signed(string path,byte[] key,string schema){
   byte[] raw=File.ReadAllBytes(path);
   string sha=Hash(raw);
   var document=JsonDocument.Parse(raw);
   var p=JsonDocument.Parse(File.ReadAllBytes(path+".proof.json"));
   var root=document.RootElement;
   var proof=p.RootElement;
   string source=root.GetProperty("source_sha256").GetString()??"";
   Need(root.GetProperty("schema").GetString()==schema
       &&proof.GetProperty("receipt_sha256").GetString()==sha
       &&proof.GetProperty("source_sha256").GetString()==source
       &&proof.GetProperty("hmac_sha256").GetString()==Hmac(key,schema,source,sha),
       "CROSS_SOURCE_HMAC_OR_SCHEMA_FAIL");
   p.Dispose();
   return (document,sha);
 }
 static bool JuneDate(object? time) {
   if(time is null)return false;
   return DateTime.TryParse(Convert.ToString(time,CultureInfo.InvariantCulture),
     CultureInfo.InvariantCulture,DateTimeStyles.AssumeLocal,out DateTime dt)
     &&dt>=new DateTime(2026,6,1)&&dt<new DateTime(2026,7,1);
 }
 static void Main(){
   Directory.CreateDirectory(Root);
   foreach(string k in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
     if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(k))){
       var v=Environment.GetEnvironmentVariable(k,EnvironmentVariableTarget.Machine);
       Need(!string.IsNullOrWhiteSpace(v),"RECOVERED_QA_CONFIG_MISSING");
       Environment.SetEnvironmentVariable(k,v);
     }
   }
   byte[] key=File.ReadAllBytes(Signer);
   Need(key.Length==32,"RECOVERED_QA_KEY_BAD");
   var (five,fiveSha)=Signed(Path.Combine(FiveRoot,"june5_exact_business.private.json"),key,FiveSchema);
   var (cross,crossSha)=Signed(Path.Combine(Root,"june5_crossdb.private.json"),key,CrossSchema);
   Need(cross.RootElement.GetProperty("june5_signed_source_receipt_sha256").GetString()==fiveSha,
        "RECOVERED_CROSSDB_PREVIOUS_SOURCE_DRIFT");
   var originals=five.RootElement.GetProperty("rows").EnumerateArray().ToDictionary(
     x=>x.GetProperty("rank").GetInt32());
   var root=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string cs=root.Descendants("connectionStrings").Descendants("add")
      .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
      .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
      ??throw new Exception("RECOVERED_ROOT_NOT_FOUND");
   Need(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)
        &&cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"QA_ROOT_WRONG");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
   AccesoDatos db=provider.Obtener(eSistema.Comercial,(byte)1);
   Need(db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
      &&db.cdnConexion.NombreBaseDatos.Equals("dbComercial001_D",StringComparison.OrdinalIgnoreCase),
      "RECOVERED_QA_WRONG_ROUTE");
   string[] allowed={"dbComercial001_D","dbComercial004_D","dbComercial100_D","dbGerencial_D"};
   var evidence=new List<object>();
   var recoveredRanks=new HashSet<int>();
   int totalAuditRows=0;
   var histograms=new List<object>();
   foreach(var database in cross.RootElement.GetProperty("searched_databases").EnumerateArray()) {
      string name=database.GetProperty("db").GetString()??"";
      if(!allowed.Contains(name))continue;
      foreach(var entry in database.GetProperty("rows").EnumerateArray()) {
        int rank=entry.GetProperty("rank").GetInt32();
        long n=entry.GetProperty("count").GetInt64();
        if(n<=0)continue;
        Need(n<=2 && originals.ContainsKey(rank),"RECOVERED_UNEXPECTED_CASE_OR_COUNT");
        var original=originals[rank];
        string id=original.GetProperty("identifier_private").GetString()??"";
        string kind=original.GetProperty("kind").GetString()??"";
        string table=kind=="PADRON"?"taPadronRuc":kind=="CAMPAIGN"?"taCampanaSupervision":"taOrdenTrabajo";
        string col=kind=="PADRON"?"NumeroDNI":kind=="CAMPAIGN"?"CodigoCampanaSupervision":"CodigoOrdenTrabajo";
        // No SELECT *, only minimum necessary fields; no names fetched.
        string sql=kind=="PADRON"?
           $"SELECT TOP(3) CodigoPadronRUC,FechaCreacion,FechaModificacion,CodigoSucursal FROM [{name}].dbo.taPadronRuc WHERE NumeroDNI=@id":
           $"SELECT TOP(3) CodigoOrdenTrabajo,CodigoEstadoOrdenTrabajo,CodigoCentroAtencion,CodigoSubTipoOrdenTrabajo,CodigoTipoOrdenTrabajo,FechaCreacion,FechaModificacion,CodigoSucursal FROM [{name}].dbo.taOrdenTrabajo WHERE CodigoOrdenTrabajo=@id";
        SqlParameter value=kind=="PADRON"?
             new("@id",SqlDbType.VarChar,12){Value=id}:
             new("@id",SqlDbType.BigInt){Value=long.Parse(id,CultureInfo.InvariantCulture)};
        DataTable rows=Q(db,sql,kind=="PADRON"?"@id varchar(12)":"@id bigint",value);
        Need(rows.Rows.Count==n,"RECOVERED_CROSSDB_COUNT_CHANGED");
        var snapshot=new List<object>();
        foreach(DataRow r in rows.Rows){
          var fields=new Dictionary<string,object?>();
          if(kind=="OT") {
             foreach(string k in new[]{"CodigoEstadoOrdenTrabajo","CodigoCentroAtencion",
               "CodigoSubTipoOrdenTrabajo","CodigoTipoOrdenTrabajo","CodigoSucursal"})
                fields[k]=Val(r,k);
             fields["FechaCreacion"]=Date(r,"FechaCreacion");
             fields["FechaModificacion"]=Date(r,"FechaModificacion");
             fields["FechaModificacion_en_junio"]=JuneDate(fields["FechaModificacion"]);
          } else {
             // Personal names are neither queried nor retained. The original
             // ticket does not contain this DNI; no person is linked to it.
             fields["CodigoSucursal"]=Val(r,"CodigoSucursal");
             fields["FechaCreacion"]=Date(r,"FechaCreacion");
             fields["FechaModificacion"]=Date(r,"FechaModificacion");
             fields["FechaModificacion_en_junio"]=JuneDate(fields["FechaModificacion"]);
             fields["id_sha256"]=Hash(Encoding.UTF8.GetBytes(Val(r,"CodigoPadronRUC")));
          }
          snapshot.Add(fields);
        }
        var audits=new List<object>();
        if(kind=="OT"&&name!="dbGerencial_D"){
           foreach(string auditTable in new[]{"taOrdenTrabajoAuditoriaCambio","taOrdenTrabajo_ModificacionIN"}){
              var query=$@"SELECT TOP (60) NombreCampo,ValorAnterior,ValorActual,FechaModificacion
               FROM [{name}].dbo.{auditTable}
               WHERE CodigoOrdenTrabajo=@id
                 AND NombreCampo IN ('CodigoCentroAtencion','CodigoEstadoOrdenTrabajo',
                                     'CodigoSubTipoOrdenTrabajo','CodigoTipoOrdenTrabajo')
               ORDER BY FechaModificacion";
              var aud=Q(db,query,"@id bigint",
                 new("@id",SqlDbType.BigInt){Value=long.Parse(id,CultureInfo.InvariantCulture)});
              foreach(DataRow r in aud.Rows) {
                // Dates and former/new code values are retained privately.
                audits.Add(new{table=auditTable,field=Val(r,"NombreCampo"),
                  before=Val(r,"ValorAnterior"),after=Val(r,"ValorActual"),
                  date=Date(r,"FechaModificacion"),
                  during_june=JuneDate(Date(r,"FechaModificacion"))});
              }
           }
        }
        recoveredRanks.Add(rank);
        totalAuditRows+=audits.Count;
        evidence.Add(new {
          rank,db=name,kind,match_count=n,
          identifier_sha256=Hash(Encoding.UTF8.GetBytes(id)),
          original_june_case_sha256=original.GetProperty("case_sha256").GetString(),
          request_original_id_corrobated=original.GetProperty("original_request_id_corrobated").GetBoolean(),
          note_id_present=original.GetProperty("historical_note_identifier_present").GetBoolean(),
          current_rows=snapshot,audit_events=audits,
          same_case_before_after_proven=false,
          source_application_contract_certified=false,
          business_fix_certified=false
        });
      }
      if(database.GetProperty("tables").TryGetProperty("taCampanaSupervision",out var campaignExists)
         &&campaignExists.GetBoolean()&&name!="dbGerencial_D"){
         try{
           var h=Q(db,$@"SELECT code_len,COUNT_BIG(*) AS n FROM (
              SELECT TOP(100) LEN(CONVERT(varchar(32),CodigoCampanaSupervision)) AS code_len
              FROM [{name}].dbo.taCampanaSupervision) x GROUP BY code_len");
           foreach(DataRow r in h.Rows)histograms.Add(new{db=name,
             code_length=Convert.ToInt32(r["code_len"]),n=Convert.ToInt64(r["n"])});
         }catch(Exception){ /* Schema inaccessible: cannot assign semantics */ }
      }
   }
   Need(evidence.Any(x=>true),"RECOVERED_NO_BUSINESS_MATCHES");
   string sourceSha=Hash(File.ReadAllBytes(Path.Combine(Root,ReaderName)));
   var receipt=new {
      schema=Schema,source_sha256=sourceSha,qa="ELSE70/dbComercial001_D",
      database_targets_allowed=allowed,
      crossdb_receipt_sha256=crossSha,june5_original_receipt_sha256=fiveSha,
      recovered_matches=evidence,
      campaign_id_length_distribution_sample100=histograms,
      data_during_june_unproven=true,
      independent_transaction_execution_unproven=true,
      business_writes=0,read_only=true
   };
   byte[] raw=JsonSerializer.SerializeToUtf8Bytes(receipt);
   string sha=Hash(raw);
   File.WriteAllBytes(Path.Combine(Root,"june5_recovered.private.json"),raw);
   File.WriteAllBytes(Path.Combine(Root,"june5_recovered.private.json.proof.json"),
    JsonSerializer.SerializeToUtf8Bytes(new{schema=ProofSchema,source_sha256=sourceSha,
      receipt_sha256=sha,hmac_sha256=Hmac(key,Schema,sourceSha,sha),read_only=true}));
   Console.WriteLine(JsonSerializer.Serialize(new{
     status="RECOVERED_QA_EVIDENCE_SIGNED",
     distinct_case_ranks=recoveredRanks.Count,
     recovered_records=evidence.Count,
     audit_events=totalAuditRows,
     receipt_sha256=sha,
     business_writes=0
   }));
 }
}
