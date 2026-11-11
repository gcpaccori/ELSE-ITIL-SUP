// ELSE-ITIL Aug 2026 QA: fixed operational OT row read, no raw business text,
// no SQL supplied by model, no DML; ELSE70/dbDistribucion_D only.
using System;
using System.Data;
using System.Data.SqlClient;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using SIELSEAccesoDatos;

internal static class AugOperationalOtRead {
  static string Sha(string value) => Convert.ToHexString(
    SHA256.HashData(Encoding.UTF8.GetBytes(value))).ToLowerInvariant();
  static string Str(DataRow row,string name) =>
    row.IsNull(name) ? "" : Convert.ToString(row[name]) ?? "";
  static bool Has(DataRow row,string name) =>
    !row.IsNull(name) && !string.IsNullOrWhiteSpace(Str(row,name));
  static int Main(string[] args) {
    if(args.Length!=1 || !Regex.IsMatch(args[0],@"^\d{4,19}$")){
      Console.Error.WriteLine("OT_CODE_REQUIRED");return 2;
    }
    try {
      foreach(string key in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
        if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(key))){
          var val=Environment.GetEnvironmentVariable(key,EnvironmentVariableTarget.Machine);
          if(string.IsNullOrWhiteSpace(val))throw new Exception("QA_SECRET_NOT_AVAILABLE");
          Environment.SetEnvironmentVariable(key,val);
        }
      }
      var xml=XDocument.Load(
        @"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
      string root=xml.Descendants("connectionStrings").Descendants("add")
        .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
        .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
        ?? throw new Exception("QA_ACCESS_ROOT_NOT_FOUND");
      if(!root.Contains("ELSE70",StringComparison.OrdinalIgnoreCase) ||
         !root.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase))
        throw new Exception("QA_ROOT_NOT_ALLOWED");
      using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(root));
      var db=provider.Obtener(eSistema.Distribucion,(byte)1);
      if(!db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase) ||
         !db.cdnConexion.NombreBaseDatos.Equals("dbDistribucion_D",StringComparison.OrdinalIgnoreCase))
        throw new Exception("QA_TARGET_NOT_ALLOWED");
      const string sql=@"SELECT TOP (2)
        CodigoOrdenTrabajo,
        CodigoEstadoOrdenTrabajo,
        CodigoClaseOrdenTrabajo,
        CodigoTipoOrdenTrabajo,
        CodigoSubTipoOrdenTrabajo,
        FechaElaboracion,
        FechaInicio,
        FechaFin
        FROM dbo.taOrdenTrabajo
        WHERE CodigoOrdenTrabajo=@ot";
      DataTable table=db.fnObtenerDatosProcedimientoDataSetN(
        "[sys].[sp_executesql]",
        new SqlParameter[] {
          new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
          new("@params",SqlDbType.NVarChar,80){Value="@ot varchar(19)"},
          new("@ot",SqlDbType.VarChar,19){Value=args[0]},
        }).Tables[0];
      if(table.Rows.Count>1)throw new Exception("DUPLICATE_OPERATIONAL_OT_QA");
      var found=table.Rows.Count==1;
      var row=found?table.Rows[0]:null;
      Console.WriteLine(JsonSerializer.Serialize(new {
        schema="else.itil.aug2026.qa.operational-ot-readonly.v1",
        qa_target="ELSE70/dbDistribucion_D",
        source="dbo.taOrdenTrabajo",
        query_id="QA_DISTRIB_OPERATIONAL_OT_BY_CODE_V1",
        order_sha256=Sha(args[0]),
        order_rows=table.Rows.Count,
        order_found=found,
        codigo_estado_orden_trabajo=found ? Str(row!,"CodigoEstadoOrdenTrabajo") : "",
        codigo_clase_orden_trabajo=found ? Str(row!,"CodigoClaseOrdenTrabajo") : "",
        codigo_tipo_orden_trabajo=found ? Str(row!,"CodigoTipoOrdenTrabajo") : "",
        codigo_subtipo_orden_trabajo=found ? Str(row!,"CodigoSubTipoOrdenTrabajo") : "",
        fecha_elaboracion_present=found && Has(row!,"FechaElaboracion"),
        fecha_inicio_present=found && Has(row!,"FechaInicio"),
        fecha_fin_present=found && Has(row!,"FechaFin"),
        read_only=true,changes_executed=false,
        read_utc=DateTime.UtcNow.ToString("O")
      }));
      return 0;
    } catch(Exception e){
      Console.Error.WriteLine("QA_OPERATIONAL_OT_READ_FAILED:"+e.GetType().Name);
      return 3;
    }
  }
}

