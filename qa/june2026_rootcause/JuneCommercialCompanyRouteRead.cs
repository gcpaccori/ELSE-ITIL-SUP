using System;
using System.Data;
using System.Data.SqlClient;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text;
using System.Security.Cryptography;
using System.Xml.Linq;
using SIELSEAccesoDatos;

// Independently verifies corporate connection factory route for companies
// 1,4,100. SQL and credentials are never disclosed, never modified.
internal static class JuneCommercialCompanyRouteRead {
 const string Root=@"C:\Temp\ELSE_ITIL_JUNE_ROOTCAUSE_20261112";
 const string Key=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.2026-commercial-route-1-4-100.v1";
 const string Proof="else.itil.qa.2026-commercial-route-1-4-100-hmac.v1";
 static void Need(bool b,string e){if(!b)throw new Exception(e);}
 static string Hash(byte[] data)=>Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();
 static void Main(){
   Directory.CreateDirectory(Root);
   foreach(var k in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
     if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(k))){
        string? val=Environment.GetEnvironmentVariable(k,EnvironmentVariableTarget.Machine);
        Need(!string.IsNullOrWhiteSpace(val),"CORPORATE_ROUTE_ENV_NOT_AVAILABLE");
        Environment.SetEnvironmentVariable(k,val);
     }
   }
   var root=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string cs=root.Descendants("connectionStrings").Descendants("add")
      .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
      .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
      ??throw new Exception("CORPORATE_ROUTE_ROOT_NOT_FOUND");
   Need(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)
        &&cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),
       "CORPORATE_ROUTE_NOT_QA");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
   var res=new System.Collections.Generic.List<object>();
   foreach(byte company in new byte[]{1,4,100}){
     try{
       AccesoDatos db=provider.Obtener(eSistema.Comercial,company);
       Need(db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase),
            "CORPORATE_ROUTE_DIFFERENT_SERVER_NOT_ALLOWED");
       string dest=db.cdnConexion.NombreBaseDatos;
       Need(new[]{"dbComercial001_D","dbComercial004_D","dbComercial100_D"}.Contains(dest),
            "CORPORATE_ROUTE_DIFFERENT_DESTINATION");
       var p=new SqlParameter[]{
         new("@stmt",SqlDbType.NVarChar,-1){Value="SELECT DB_NAME() AS database_name"},
         new("@params",SqlDbType.NVarChar,2){Value=""}
       };
       var data=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",p);
       Need(data!=null&&data.Tables.Count==1&&data.Tables[0].Rows.Count==1,
            "CORPORATE_ROUTE_DB_QUERY_FAILED");
       string actual=Convert.ToString(data!.Tables[0].Rows[0]["database_name"])??"";
       Need(actual==dest,"CORPORATE_ROUTE_CLAIM_MISMATCH");
       res.Add(new{company=(int)company,target_db=dest,actual_db=actual,
          route_verified=true,qa_server="ELSE70"});
     }catch(Exception e){
       res.Add(new{company=(int)company,target_db="",actual_db="",
          route_verified=false,error_type=e.GetType().Name,qa_server="ELSE70"});
     }
   }
   string source=Hash(File.ReadAllBytes(Path.Combine(Root,"JuneCommercialCompanyRouteRead.cs")));
   var output=new{schema=Schema,source_sha256=source,read_only=true,
      qa_server="ELSE70",rows=res,business_modifications=0};
   byte[] raw=JsonSerializer.SerializeToUtf8Bytes(output);
   string digest=Hash(raw);byte[] key=File.ReadAllBytes(Key);
   Need(key.Length==32,"CORPORATE_HMAC_INVALID");
   string mac=Convert.ToHexString(HMACSHA256.HashData(key,
      Encoding.UTF8.GetBytes(Schema+":"+source+":"+digest))).ToLowerInvariant();
   string destpath=Path.Combine(Root,"commercial_company_routes.private.json");
   File.WriteAllBytes(destpath,raw);
   File.WriteAllBytes(destpath+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
     schema=Proof,source_sha256=source,receipt_sha256=digest,hmac_sha256=mac,read_only=true}));
   Console.WriteLine(JsonSerializer.Serialize(new{
      status="COMPANY_ROUTE_QA_PROBED",company_count=3,
      verified=res.Count(x=>JsonSerializer.SerializeToElement(x).GetProperty("route_verified").GetBoolean()),
      receipt_sha256=digest}));
 }
}
