// Fixed QA-only March functional source availability probes; no ticket details / SQL DML.
using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Xml.Linq;
using SIELSEAccesoDatos;
internal static class MarchDomainSources {
 const string Root=@"C:\Temp\ELSE_ITIL_MARCH10_QA_20261112";
 const string Schema="else.itil.qa.march2026-domain-source-probes.v1";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 record Scope(string Group,eSistema System,byte Company,string Db,string DbSchema,string Table);
 static readonly Scope[] Sources={
   new("COMMERCIAL_BILLING",eSistema.Comercial,1,"dbComercial001_D","dbo","taFacturacion"),
   new("COMMERCIAL_BILLING",eSistema.Comercial,1,"dbComercial001_D","dbo","taComprobante"),
   new("COMMERCIAL_CASH",eSistema.Comercial,3,"dbComercial003_D","dbo","taCaja"),
   new("COMMERCIAL_CASH",eSistema.Comercial,3,"dbComercial003_D","dbo","taCobranza"),
   new("MGD",eSistema.MGDv2,1,"dbMGD_D","mgd","taDocumento"),
   new("MGD",eSistema.MGDv2,1,"dbMGD_D","mgd","taExpediente"),
   new("MGD",eSistema.MGDv2,1,"dbMGD_D","firma","taTrabajadorFirmaMGD"),
   new("IAM",eSistema.Seguridad,1,"dbSeguridad_D","dbo","taUsuario"),
   new("IAM",eSistema.Seguridad,1,"dbSeguridad_D","dbo","taGrupoUsuarioModulo"),
 };
 static string Hash(byte[] raw)=>Convert.ToHexString(SHA256.HashData(raw)).ToLowerInvariant();
 static void Need(bool b,string c){if(!b)throw new Exception(c);}
 static DataTable Q(AccesoDatos db,string sql)=>db.fnObtenerDatosProcedimientoDataSetN(
    "[sys].[sp_executesql]",new SqlParameter[]{
      new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
      new("@params",SqlDbType.NVarChar,10){Value=""}
    }).Tables[0];
 static int Main(){
  try{
    Directory.CreateDirectory(Root);
    foreach(var k in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
      if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(k))){
        string? v=Environment.GetEnvironmentVariable(k,EnvironmentVariableTarget.Machine);
        Need(!string.IsNullOrWhiteSpace(v),"QA_CONNECTOR_MISSING");
        Environment.SetEnvironmentVariable(k,v);
      }
    }
    var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
    string cs=xml.Descendants("connectionStrings").Descendants("add")
      .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
      .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
      ??throw new Exception("QA_ROOT_NOT_FOUND");
    Need(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase) &&
        cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"QA_ROOT_NOT_ALLOWED");
    using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
    var conn=new Dictionary<string,AccesoDatos>();
    foreach(var scope in Sources){
       string key=scope.System+":"+scope.Company;
       if(conn.ContainsKey(key))continue;
       var x=provider.Obtener(scope.System,scope.Company);
       Need(x.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase) &&
          x.cdnConexion.NombreBaseDatos.Equals(scope.Db,StringComparison.OrdinalIgnoreCase),
          "ROUTE_TO_WRONG_QA_DB");
       conn[key]=x;
    }
    var results=new List<object>();
    foreach(var scope in Sources){
      string key=scope.System+":"+scope.Company;
      string name=$"[{scope.DbSchema}].[{scope.Table}]";
      try{
        var rows=Q(conn[key],$"SELECT TOP (1) 1 AS source_hit FROM {name}");
        Need(rows.Rows.Count<=1,"SOURCE_QUERY_MORE_THAN_ONE");
        results.Add(new{group=scope.Group,company=scope.Company,server="ELSE70",
          database=scope.Db,source=scope.DbSchema+"."+scope.Table,
          status=rows.Rows.Count==1?"ROW_OBSERVED":"TABLE_EMPTY",
          query_rows=rows.Rows.Count,error="",read_only=true});
      }catch(Exception ex){
        results.Add(new{group=scope.Group,company=scope.Company,server="ELSE70",
          database=scope.Db,source=scope.DbSchema+"."+scope.Table,
          status="BLOCKED",query_rows=0,error=ex.GetType().Name,read_only=true});
      }
    }
    byte[] source=File.ReadAllBytes(Path.Combine(Root,"MarchDomainSources.cs"));
    string sourceSha=Hash(source);
    var receipt=new{schema=Schema,worker="ELSE62",qa_server="ELSE70",
        source_sha256=sourceSha,queries=Sources.Length,
        observed=results.Count(x=>JsonSerializer.SerializeToElement(x).GetProperty("status").GetString()=="ROW_OBSERVED"),
        empty=results.Count(x=>JsonSerializer.SerializeToElement(x).GetProperty("status").GetString()=="TABLE_EMPTY"),
        blocked=results.Count(x=>JsonSerializer.SerializeToElement(x).GetProperty("status").GetString()=="BLOCKED"),
        results, business_rows_returned=false,read_only=true,changes_executed=false,
        read_utc=DateTime.UtcNow.ToString("O")};
    byte[] body=JsonSerializer.SerializeToUtf8Bytes(receipt);
    string path=Path.Combine(Root,"march_domain_sources.private.json");
    File.WriteAllBytes(path,body);
    byte[] keybytes=File.ReadAllBytes(Signer);
    Need(keybytes.Length==32,"QA_SIGNER_MISSING");
    string bodySha=Hash(body);
    string signature=Convert.ToHexString(HMACSHA256.HashData(keybytes,
       Encoding.UTF8.GetBytes(Schema+":"+sourceSha+":"+bodySha))).ToLowerInvariant();
    File.WriteAllBytes(path+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
       schema="else.itil.qa.march2026-domain-sources-hmac.v1",source_sha256=sourceSha,
       receipt_sha256=bodySha,hmac_sha256=signature,worker="ELSE62",read_only=true}));
    Console.WriteLine(JsonSerializer.Serialize(new{
      status="QA_MARCH_SOURCE_PROBES_FINISHED",receipt.queries,receipt.observed,
      receipt.empty,receipt.blocked,source_sha256=sourceSha,receipt_sha256=bodySha}));
    return 0;
  }catch(Exception ex){
     Console.Error.WriteLine("MARCH_DOMAIN_SOURCE_PROBE_FAILED:"+ex.GetType().Name);
     return 3;
  }
 }
}
