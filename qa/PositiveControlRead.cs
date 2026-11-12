// ELSE ITIL QA: independently exercise positive exact OT and supply lookups.
// Returns only bool, dates and route, never the source OT or supply keys.
using System;
using System.Data;
using System.Data.SqlClient;
using System.Linq;
using System.Text.Json;
using System.Xml.Linq;
using SIELSEAccesoDatos;
internal static class PositiveControlRead{
 static int Main(){
  try{
   foreach(var key in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
    if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(key))){
     var value=Environment.GetEnvironmentVariable(key,EnvironmentVariableTarget.Machine);
     if(string.IsNullOrWhiteSpace(value))throw new Exception("MISSING_QA_CONFIG");
     Environment.SetEnvironmentVariable(key,value);
    }
   }
   var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string cs=xml.Descendants("connectionStrings").Descendants("add")
      .Where(e=>(string?)e.Attribute("name")=="ConexionSIELSE")
      .Select(e=>(string?)e.Attribute("connectionString")).Single()
      ??throw new Exception("NO_QA_ROOT");
   if(!cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)||
       !cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase))
    throw new Exception("QA_ROOT_INVALID");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
   var results=new System.Collections.Generic.List<object>();
   foreach(byte company in new byte[]{1,3}){
    var db=provider.Obtener(eSistema.Comercial,company);
    string dest="dbComercial"+company.ToString("000")+"_D";
    if(!db.cdnConexion.NombreBaseDatos.Equals(dest,StringComparison.OrdinalIgnoreCase)
      ||!db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase))
      throw new Exception("BUSINESS_DB_ROUTE_NOT_EXACT");
    DataTable Read(string sql,params SqlParameter[] ps){
     var all=new SqlParameter[ps.Length+2];
     all[0]=new("@stmt",SqlDbType.NVarChar,-1){Value=sql};
     all[1]=new("@params",SqlDbType.NVarChar,150){Value=string.Join(",",
        ps.Select(p=>p.ParameterName+" "+(p.SqlDbType==SqlDbType.DateTime?"datetime":"bigint")))};
     Array.Copy(ps,0,all,2,ps.Length);
     return db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",all).Tables[0];
    }
    const string findAug=@"SELECT TOP(1) CodigoOrdenTrabajo,
      CONVERT(varchar(10),FechaRegistroSolicitud,120) AS registration_date
      FROM dbo.taOrdenTrabajo
      WHERE FechaRegistroSolicitud>=@start AND FechaRegistroSolicitud<@end
      ORDER BY FechaRegistroSolicitud DESC";
    var latest=Read(findAug,
       new SqlParameter("@start",SqlDbType.DateTime){Value=new DateTime(2026,8,1)},
       new SqlParameter("@end",SqlDbType.DateTime){Value=new DateTime(2026,9,1)});
    bool august=latest.Rows.Count==1;
    long ot=august?Convert.ToInt64(latest.Rows[0]["CodigoOrdenTrabajo"]):0;
    string date=august?Convert.ToString(latest.Rows[0]["registration_date"])??"":"";
    int exact=august?Read(@"SELECT TOP(2) 1 AS hit FROM dbo.taOrdenTrabajo
          WHERE CodigoOrdenTrabajo=@ot",
          new SqlParameter("@ot",SqlDbType.BigInt){Value=ot}).Rows.Count:0;
    var supply=Read("SELECT TOP(1) CodigoSuministro FROM dbo.taSuministro WHERE CodigoSuministro IS NOT NULL");
    long supplyKey=supply.Rows.Count==1?Convert.ToInt64(supply.Rows[0]["CodigoSuministro"]):0;
    int supplyExact=supplyKey>0?Read(
        @"SELECT TOP(2) 1 AS hit FROM dbo.taSuministro WHERE CodigoSuministro=@supply",
        new SqlParameter("@supply",SqlDbType.BigInt){Value=supplyKey}).Rows.Count:0;
    var linked=Read(@"SELECT TOP(1) CodigoOrdenTrabajo,CodigoSuministro
        FROM dbo.taOrdenTrabajo WHERE CodigoSuministro IS NOT NULL AND CodigoSuministro>0");
    bool linkedYes=linked.Rows.Count==1;
    int exactLink=0;
    if(linkedYes){
      long linkedOt=Convert.ToInt64(linked.Rows[0]["CodigoOrdenTrabajo"]);
      long linkedSupply=Convert.ToInt64(linked.Rows[0]["CodigoSuministro"]);
      exactLink=Read(@"SELECT TOP(2) 1 AS hit FROM dbo.taOrdenTrabajo
          WHERE CodigoOrdenTrabajo=@ot AND CodigoSuministro=@supply",
          new SqlParameter("@ot",SqlDbType.BigInt){Value=linkedOt},
          new SqlParameter("@supply",SqlDbType.BigInt){Value=linkedSupply}).Rows.Count;
    }
    results.Add(new{
     company,qa_target="ELSE70/"+dest,aug2026_ot_positive_sample_found=august,
     aug2026_ot_sample_registration_date=date,
     aug2026_ot_exact_lookup_pass=august&&exact==1,
     supply_positive_sample_found=supplyKey>0,
     supply_exact_lookup_pass=supplyExact==1,
     ot_supply_link_sample_found=linkedYes,
     ot_supply_exact_link_lookup_pass=linkedYes&&exactLink==1,
     read_only=true
    });
   }
   Console.WriteLine(JsonSerializer.Serialize(new{
    schema="else.itil.qa.company-positive-control.v1",cases=results,
    no_identifiers_returned=true,read_only=true,mutations=0
   }));return 0;
  }catch(Exception ex){Console.Error.WriteLine("QA_POSITIVE_CONTROL_FAIL:"+ex.GetType().Name);return 3;}
 }
}

