// Read-only QA census for exactly Jan 1-10 2026 inclusive.
// Does not read ticket text, names, passwords, solutions or business identifiers.
using System;
using System.Data;
using System.Data.SqlClient;
using System.Globalization;
using System.Linq;
using System.Text.Json;
using System.Xml.Linq;
using SIELSEAccesoDatos;

internal static class Jan10QaCount {
    public static int Main() {
        try {
            foreach(string key in new[]{
                "SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"
            }) {
                if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(
                    key,EnvironmentVariableTarget.Process))) {
                    string value=Environment.GetEnvironmentVariable(
                        key,EnvironmentVariableTarget.Machine) ?? "";
                    if(string.IsNullOrWhiteSpace(value))
                        throw new InvalidOperationException("QA_ENV_UNAVAILABLE");
                    Environment.SetEnvironmentVariable(key,value,
                        EnvironmentVariableTarget.Process);
                }
            }
            var xml=XDocument.Load(
                @"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
            string cs=xml.Descendants("connectionStrings").Descendants("add")
                .Where(e=>(string?)e.Attribute("name")=="ConexionSIELSE")
                .Select(e=>(string?)e.Attribute("connectionString"))
                .Single() ?? throw new Exception("QA_ROOT_MISSING");
            if(!cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase) ||
               !cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("WRONG_QA_ROOT");
            using IConexionBD host=new ConexionBD(new CadenaConexionCollection(cs));
            var db=host.Obtener(eSistema.ITIL,(byte)1);
            if(db.cdnConexion.NombreServidor!="ELSE70" ||
               db.cdnConexion.NombreBaseDatos!="dbITIL_D")
                throw new InvalidOperationException("WRONG_ITIL_DATABASE");
            const string sql = @"SELECT
                  COUNT_BIG(*) AS case_count,
                  COUNT_BIG(DISTINCT CodigoIncidente) AS distinct_case_count,
                  MIN(FechaSolicitud) AS first_seen,
                  MAX(FechaSolicitud) AS last_seen
                FROM dbo.taIncidente
                WHERE FechaSolicitud>=@start AND FechaSolicitud<@end";
            var result=db.fnObtenerDatosProcedimientoDataSetN(
                "[sys].[sp_executesql]",new SqlParameter[]{
                    new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
                    new("@params",SqlDbType.NVarChar,100){
                        Value="@start datetime,@end datetime"},
                    new("@start",SqlDbType.DateTime){
                        Value=new DateTime(2026,1,1)},
                    new("@end",SqlDbType.DateTime){
                        Value=new DateTime(2026,1,11)}
                }).Tables[0];
            if(result.Rows.Count!=1)
                throw new Exception("INVALID_QA_COUNT_RESULT");
            var r=result.Rows[0];
            long count=Convert.ToInt64(r["case_count"],CultureInfo.InvariantCulture);
            long unique=Convert.ToInt64(r["distinct_case_count"],
                                        CultureInfo.InvariantCulture);
            if(count!=638 || unique!=638)
                throw new Exception("SNAPSHOT_SCOPE_DRIFT");
            Console.WriteLine(JsonSerializer.Serialize(new{
                schema="else.itil.jan10.qa-count.v1",
                qa_source="ELSE70/dbITIL_D/dbo.taIncidente",
                period_start_inclusive="2026-01-01",
                period_end_exclusive="2026-01-11",
                case_count=count,
                unique_cases=unique,
                first_seen=Convert.ToDateTime(r["first_seen"]).ToString("yyyy-MM-dd"),
                last_seen=Convert.ToDateTime(r["last_seen"]).ToString("yyyy-MM-dd"),
                query_read_only=true,
                solutions_not_read=true,
                corporate_mutations=false
            }));
            return 0;
        } catch(Exception ex) {
            string code=ex.Message=="SNAPSHOT_SCOPE_DRIFT"?
                ex.Message:"QA_CENSUS_UNAVAILABLE";
            Console.WriteLine(JsonSerializer.Serialize(new{
                status="QA_CENSUS_FAILED",error_code=code
            }));
            return 2;
        }
    }
}
