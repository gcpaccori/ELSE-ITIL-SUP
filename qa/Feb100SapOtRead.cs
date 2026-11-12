// QA-only fixed SAP/OT evidence read for a uniquely reported OT identifier.
// ELSE70 / dbDistribucion_D; no SQL from Qwen, no DML, no raw messages.
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

internal static class Feb100SapOtRead {
    const string Target="ELSE70/dbDistribucion_D";
    static string Sha(string v)=>Convert.ToHexString(
        SHA256.HashData(Encoding.UTF8.GetBytes(v))).ToLowerInvariant();
    static string Str(DataRow r,string col) =>
        r.IsNull(col) ? "" : Convert.ToString(r[col]) ?? "";
    static DataTable Select(AccesoDatos db,string query,string sql,string ot) {
        if(!sql.TrimStart().StartsWith("SELECT TOP (",StringComparison.OrdinalIgnoreCase))
            throw new Exception("SQL_TEMPLATE_NOT_FIXED_SELECT");
        return db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",
          new SqlParameter[] {
            new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
            new("@params",SqlDbType.NVarChar,80){Value="@ot varchar(19)"},
            new("@ot",SqlDbType.VarChar,19){Value=ot},
          }).Tables[0];
    }
    static int Main(string[] args) {
        if(args.Length!=1 || !Regex.IsMatch(args[0],@"^\d{4,19}$")) {
            Console.Error.WriteLine("OT_IDENTIFIER_INVALID"); return 2;
        }
        try {
            foreach(var key in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}) {
                if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(key))) {
                    var v=Environment.GetEnvironmentVariable(key,EnvironmentVariableTarget.Machine);
                    if(string.IsNullOrWhiteSpace(v))throw new Exception("QA_ACCESS_NOT_AVAILABLE");
                    Environment.SetEnvironmentVariable(key,v);
                }
            }
            var xml=XDocument.Load(
              @"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
            string cs=xml.Descendants("connectionStrings").Descendants("add")
              .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
              .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
              ?? throw new Exception("QA_ROOT_UNAVAILABLE");
            if(!cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase) ||
               !cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase))
                throw new Exception("QA_ROOT_INVALID");
            using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
            var db=provider.Obtener(eSistema.Distribucion,(byte)1);
            if(!db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
               || !db.cdnConexion.NombreBaseDatos.Equals("dbDistribucion_D",
                                                         StringComparison.OrdinalIgnoreCase))
                throw new Exception("QA_TARGET_INVALID");
            const string sqlOrder=@"SELECT TOP (2) CodigoOrdenTrabajo,
                  CodigoEstadoEnvioSAP,CodigoClaseOrdenTrabajoSAP,NumeroCoSAP
                  FROM dbo.taOrdenTrabajoSAP WHERE CodigoOrdenTrabajo=@ot";
            const string sqlResponse=@"SELECT TOP (5) CodigoOrdenTrabajo,
                  Estado,Mensaje,OrdenCO
                  FROM dbo.taOrdenTrabajoSAPEnvioRespuesta
                  WHERE CodigoOrdenTrabajo=@ot ORDER BY CodigoOrdenTrabajo";
            DataTable order=Select(db,"QA_DISTRIB_SAP_ORDER_BY_OT",sqlOrder,args[0]);
            DataTable response=Select(db,"QA_DISTRIB_SAP_RESPONSE_BY_OT",sqlResponse,args[0]);
            if(order.Rows.Count>1)throw new Exception("OT_NOT_UNIQUE_IN_QA");
            string state=order.Rows.Count==1?Str(order.Rows[0],"CodigoEstadoEnvioSAP"):"";
            string orderClass=order.Rows.Count==1?Str(order.Rows[0],"CodigoClaseOrdenTrabajoSAP"):"";
            bool sapNumber=order.Rows.Count==1 && !string.IsNullOrWhiteSpace(
                Str(order.Rows[0],"NumeroCoSAP"));
            bool anyMessage=response.Rows.Cast<DataRow>().Any(x=>
                !string.IsNullOrWhiteSpace(Str(x,"Mensaje")));
            bool anyOrderCo=response.Rows.Cast<DataRow>().Any(x=>
                !string.IsNullOrWhiteSpace(Str(x,"OrdenCO")));
            Console.WriteLine(JsonSerializer.Serialize(new {
                schema="else.itil.qa.feb100.sap-ot-readonly.v1",
                query_ids=new[]{"QA_DISTRIB_SAP_ORDER_BY_OT","QA_DISTRIB_SAP_RESPONSE_BY_OT"},
                qa_target=Target,
                sources=new[]{"dbo.taOrdenTrabajoSAP","dbo.taOrdenTrabajoSAPEnvioRespuesta"},
                order_sha256=Sha(args[0]),
                order_rows=order.Rows.Count,
                order_found=order.Rows.Count==1,
                codigo_estado_envio_sap=state,
                codigo_clase_orden_sap=orderClass,
                numero_co_sap_present=sapNumber,
                response_rows_up_to5=response.Rows.Count,
                response_message_present=anyMessage,
                response_orden_co_present=anyOrderCo,
                response_sample_limited=response.Rows.Count==5,
                read_only=true,changes_executed=false,
                read_utc=DateTime.UtcNow.ToString("O")
            }));
            return 0;
        } catch(Exception ex) {
            Console.Error.WriteLine("QA_OT_SAP_READ_UNAVAILABLE:"+ex.GetType().Name);
            return 3;
        }
    }
}

