// Independent QA integration test for 5 SIELSE module read profiles.
// Selects actual company-specific existing OT witnesses, probes multiple
// required relational tables, emits ONLY counters/flags; no IDs or changes.
using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.Globalization;
using System.Linq;
using System.Text.Json;
using System.Xml.Linq;
using SIELSEAccesoDatos;
internal static class FunctionalQueries{
 static int Main(){
  try{
   foreach(string key in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
    if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(key))){
     string? val=Environment.GetEnvironmentVariable(key,EnvironmentVariableTarget.Machine);
     if(string.IsNullOrWhiteSpace(val))throw new Exception("QA_AUTH_MISSING");
     Environment.SetEnvironmentVariable(key,val);
    }
   }
   var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string cs=xml.Descendants("connectionStrings").Descendants("add")
    .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
    .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
    ??throw new Exception("NO_QA_CONFIG");
   if(!cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)||
      !cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase))
     throw new Exception("QA_ROOT_INVALID");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
   var profiles=new List<object>();
   foreach(byte company in new byte[]{1,3}){
    string target="dbComercial"+company.ToString("000")+"_D";
    var db=provider.Obtener(eSistema.Comercial,company);
    if(!db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase) ||
       !db.cdnConexion.NombreBaseDatos.Equals(target,StringComparison.OrdinalIgnoreCase))
       throw new Exception("WRONG_BUSINESS_COMPANY_DB");
    DataTable Read(string sql,params SqlParameter[] ps){
      var args=new SqlParameter[2+ps.Length];
      args[0]=new("@stmt",SqlDbType.NVarChar,-1){Value=sql};
      args[1]=new("@params",SqlDbType.NVarChar,120){
        Value=string.Join(",",ps.Select(x=>x.ParameterName+" "+
          (x.SqlDbType==SqlDbType.BigInt?"bigint":"datetime")))};
      Array.Copy(ps,0,args,2,ps.Length);
      try{
       return db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args).Tables[0];
      }catch(SqlException e){
        string table=sql.Contains("FROM dbo.")?
          sql.Substring(sql.IndexOf("FROM dbo.")+9).Split(new[]{' ','\r','\n'},StringSplitOptions.RemoveEmptyEntries)[0]:"UNKNOWN";
        Console.Error.WriteLine("FIXED_QUERY_FAILURE TABLE="+table+" NUM="+e.Number+" COMPANY="+company);
        throw;
      }
    }
    SqlParameter Param(long key)=>new("@ot",SqlDbType.BigInt){Value=key};
    const string august=@"SELECT TOP(1) o.CodigoOrdenTrabajo,o.CodigoSuministro,
       CONVERT(varchar(10),o.FechaRegistroSolicitud,120) AS sample_date
       FROM dbo.taOrdenTrabajo o
       INNER JOIN dbo.taPresupuesto p ON p.CodigoOrdenTrabajo=o.CodigoOrdenTrabajo
       WHERE o.FechaRegistroSolicitud>=@start
         AND o.FechaRegistroSolicitud<@end
       ORDER BY o.FechaRegistroSolicitud DESC";
    const string historical=@"SELECT TOP(1)
       o.CodigoOrdenTrabajo,o.CodigoSuministro,
       CONVERT(varchar(10),o.FechaRegistroSolicitud,120) AS sample_date
       FROM dbo.taOrdenTrabajo o
       INNER JOIN dbo.taPresupuesto p ON p.CodigoOrdenTrabajo=o.CodigoOrdenTrabajo
       ORDER BY o.FechaRegistroSolicitud DESC";
    var otSample=(company==1) ?
       Read(august,
         new SqlParameter("@start",SqlDbType.DateTime){Value=new DateTime(2026,8,1)},
         new SqlParameter("@end",SqlDbType.DateTime){Value=new DateTime(2026,9,1)})
       :Read(historical);
    bool budgetWitness=otSample.Rows.Count==1;
    if(!budgetWitness){
      const string fall=@"SELECT TOP(1)
        CodigoOrdenTrabajo,CodigoSuministro,
        CONVERT(varchar(10),FechaRegistroSolicitud,120) AS sample_date
        FROM dbo.taOrdenTrabajo ORDER BY FechaRegistroSolicitud DESC";
      otSample=Read(fall);
    }
    if(otSample.Rows.Count!=1)throw new Exception("QA_OT_WITNESS_MISSING");
    var row=otSample.Rows[0];
    long ot=Convert.ToInt64(row["CodigoOrdenTrabajo"],CultureInfo.InvariantCulture);
    long supply=row.IsNull("CodigoSuministro")?0:
         Convert.ToInt64(row["CodigoSuministro"],CultureInfo.InvariantCulture);
    string date=Convert.ToString(row["sample_date"])??"";
    if(company==1 && budgetWitness && !date.StartsWith("2026-08"))
      throw new Exception("AUGUST_POSITIVE_BUDGET_WITNESS_WRONG_DATE");
    int? Count(string table){
      var exist=Read("SELECT CASE WHEN OBJECT_ID('dbo."+table+"','U') IS NULL THEN 0 ELSE 1 END AS allowed_table");
      if(Convert.ToInt32(exist.Rows[0]["allowed_table"])==0)return null;
      string sql="SELECT TOP(2) 1 AS hit FROM dbo."+table+" WHERE CodigoOrdenTrabajo=@ot";
      var result=Read(sql,Param(ot));
      if(result.Rows.Count>2)throw new Exception("QA_COUNT_NOT_BOUNDED");
      return result.Rows.Count;
    }
    var otLookup=Read(@"SELECT TOP(1) CodigoEstadoOrdenTrabajo,
        FechaEjecucionInicio,FechaEjecucionFin,CodigoSuministro
        FROM dbo.taOrdenTrabajo WHERE CodigoOrdenTrabajo=@ot",Param(ot));
    if(otLookup.Rows.Count!=1)throw new Exception("QA_OT_SAMPLE_REBIND_FAILED");
    var record=otLookup.Rows[0];
    int? budget=Count("taPresupuesto");
    int? resources=Count("taPresupuestoTrabajoRecurso");
    int? voucher=Count("taComprobante");
    int? osinergmin=Count("taOrdenTrabajoEstadoHistorico");
    int? changeLog=Count("taOrdenTrabajoAuditoriaCambio");
    int? installAudit=Count("taOrdenTrabajo_ModificacionIN");
    int? installation=Count("taOTInstalacion");
    int? interior=Count("taOTInstalacionInterior");
    int? meterSupply=null;
    if(supply>0){
      var dt=Read(@"SELECT TOP(2) 1 AS hit
          FROM dbo.taMedidorSuministro WHERE CodigoSuministro=@supply",
          new SqlParameter("@supply",SqlDbType.BigInt){Value=supply});
      meterSupply=dt.Rows.Count;
    }
    int estado=Convert.ToInt32(record["CodigoEstadoOrdenTrabajo"],CultureInfo.InvariantCulture);
    var state=Read(@"SELECT TOP(1) NombreEstadoOrdenTrabajo
        FROM dbo.gnEstadoOrdenTrabajo WHERE CodigoEstadoOrdenTrabajo=@estado",
        new SqlParameter("@estado",SqlDbType.BigInt){Value=estado});
    profiles.Add(new{
      company,qa_target="ELSE70/"+target,
      sample_ot_from_august_2026=date.StartsWith("2026-08"),
      sample_ot_witness_in_budget=budgetWitness,
      ot_exact_rebound=true,budget_rows_limited=budget,
      resource_rows_limited=resources,
      voucher_rows_limited=voucher,
      osinergmin_history_rows_limited=osinergmin,
      change_log_rows_limited=changeLog,
      installation_audit_rows_limited=installAudit,
      installation_module_rows_limited=installation,
      interior_installation_rows_limited=interior,
      meter_supply_rows_limited=meterSupply,
      ot_state_catalog_found=state.Rows.Count==1,
      execution_dates_present=!record.IsNull("FechaEjecucionInicio")&&
           !record.IsNull("FechaEjecucionFin"),
      read_only=true,changes_executed=false
    });
   }
   Console.WriteLine(JsonSerializer.Serialize(new{
     schema="else.itil.qa.functional-business-profiles-positive-witness.v1",
     profile_count=5,companies=profiles,
     no_raw_business_keys_returned=true,
     read_only=true,changes_executed=false
   }));return 0;
  }catch(Exception ex){
    Console.Error.WriteLine("QA_FUNCTIONAL_SELECT_FAILED:"+ex.GetType().Name);
    return 3;
  }
 }
}


