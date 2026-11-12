// QA-only distribution metadata probe, no business rows and no model input.
using System;
using System.Data;
using System.Data.SqlClient;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Xml.Linq;
using SIELSEAccesoDatos;
internal class AugOtSchemaProbe {
  static int Main() {
    try {
      foreach(string key in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
        if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(key))){
          string? value=Environment.GetEnvironmentVariable(key,EnvironmentVariableTarget.Machine);
          if(string.IsNullOrWhiteSpace(value))throw new Exception("QA_ACCESS_NOT_AVAILABLE");
          Environment.SetEnvironmentVariable(key,value);
        }
      }
      var xml=XDocument.Load(
        @"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
      string cs=xml.Descendants("connectionStrings").Descendants("add")
        .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
        .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
        ?? throw new Exception("QA_ROOT_MISSING");
      if(!cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase) ||
         !cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase))
        throw new Exception("QA_ROOT_NOT_ALLOWED");
      using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
      var db=provider.Obtener(eSistema.Distribucion,(byte)1);
      if(!db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
       || !db.cdnConexion.NombreBaseDatos.Equals("dbDistribucion_D",StringComparison.OrdinalIgnoreCase))
        throw new Exception("NOT_DISTRIBUCION_QA");
      const string stmt=@"SELECT TOP (100)
          SCHEMA_NAME(t.schema_id) AS schema_name,
          t.name AS table_name,
          c.name AS column_name
        FROM sys.tables t INNER JOIN sys.columns c ON c.object_id=t.object_id
        WHERE t.name IN ('taOrdenTrabajo','taOrdenTrabajoSAP',
                         'taOrdenTrabajoMantenimiento')
        ORDER BY t.name,c.column_id";
      DataTable table=db.fnObtenerDatosProcedimientoDataSetN(
        "[sys].[sp_executesql]",
        new SqlParameter[]{
          new("@stmt",SqlDbType.NVarChar,-1){Value=stmt},
          new("@params",SqlDbType.NVarChar,5){Value=""}
        }).Tables[0];
      var rows=new List<object>();
      foreach(DataRow r in table.Rows){
        rows.Add(new {
          schema_name=Convert.ToString(r["schema_name"]),
          table_name=Convert.ToString(r["table_name"]),
          column_name=Convert.ToString(r["column_name"])
        });
      }
      Console.WriteLine(JsonSerializer.Serialize(new {
        schema="else.itil.aug2026.qa.distribution-ot-metadata.v1",
        qa_target="ELSE70/dbDistribucion_D",
        query_type="FIXED_SYS_TABLES_METADATA_ONLY",
        returned_columns=rows.Count,
        rows,
        read_only=true, changes_executed=false,
        utc=DateTime.UtcNow.ToString("O")
      }));
      return 0;
    } catch(Exception e) {
      Console.Error.WriteLine("QA_METADATA_PROBE_FAILED:"+e.GetType().Name);
      return 3;
    }
  }
}
