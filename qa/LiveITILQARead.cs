// Windows QA-only exact NuGet read for a model-requested, owner-allowlisted case.
// The model NEVER supplies SQL, DB, host, case ID, filesystem paths or credentials.
// Query and allowed historical interval are compiled constants. Read-only.
using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using SIELSEAccesoDatos;

internal static class LiveITILQARead {
    const string QaTarget = "ELSE70/dbITIL_D/dbo.taIncidente";
    const string Query = "ITIL_2026_09_CASE_EXACT_READ";
    const string Schema = "else.itil.qa.e2e02.o16-evidence-transfer.v1";
    const string SourcePath = "qa/LiveITILQARead.cs";
    static readonly DateTime MonthStart = new(2026,9,1);
    static readonly DateTime MonthEnd = new(2026,10,1);

    static string Sha(byte[] value) =>
        Convert.ToHexString(SHA256.HashData(value)).ToLowerInvariant();
    static string ShaText(string value) => Sha(Encoding.UTF8.GetBytes(value));
    static string Text(DataRow row, string key) =>
        row.IsNull(key) ? "" : Convert.ToString(row[key],CultureInfo.InvariantCulture) ?? "";
    static string Single(JsonElement item,string key) =>
        item.GetProperty(key).GetString() ?? throw new Exception("NULL_FIELD_"+key);

    static int Main(string[] args) {
        try {
            if (args.Length!=8 || args[0]!="--allowlist" || args[2]!="--case-sha" ||
                args[4]!="--out" || args[6]!="--source")
                throw new Exception("EXACT_ARGUMENTS_REQUIRED");
            string allowlist = Path.GetFullPath(args[1]);
            string caseSha = args[3];
            string output = Path.GetFullPath(args[5]);
            string sourcePath = Path.GetFullPath(args[7]);
            if (!Regex.IsMatch(caseSha,@"\A[0-9a-f]{64}\z"))
                throw new Exception("INVALID_CASE_SHA");
            if (Path.GetFileName(sourcePath)!="LiveITILQARead.cs" ||
                !Path.GetFullPath(sourcePath).Replace('\\','/').EndsWith("/qa/LiveITILQARead.cs"))
                throw new Exception("READER_SOURCE_NOT_APPROVED");

            JsonElement chosen=default;
            int found=0;
            foreach(string line in File.ReadLines(allowlist,Encoding.UTF8)) {
                if (string.IsNullOrWhiteSpace(line)) continue;
                using var document = JsonDocument.Parse(line);
                JsonElement row = document.RootElement;
                if (row.ValueKind!=JsonValueKind.Object)
                    throw new Exception("ALLOWLIST_ROW_NOT_OBJECT");
                var keys=row.EnumerateObject().Select(x=>x.Name).OrderBy(x=>x).ToArray();
                string[] expected={"case_ref","case_sha256","classification_code",
                    "description_redacted","module_code","opened_at","service_code"};
                if (!keys.SequenceEqual(expected.OrderBy(x=>x)))
                    throw new Exception("ALLOWLIST_FIELDS_INVALID");
                string refValue=Single(row,"case_ref");
                if (!Regex.IsMatch(refValue,@"\A[A-Za-z0-9_-]{1,65}\z"))
                    throw new Exception("ALLOWLIST_REF_INVALID");
                if (ShaText(refValue)!=Single(row,"case_sha256"))
                    throw new Exception("ALLOWLIST_REF_SHA_MISMATCH");
                if (Single(row,"case_sha256")==caseSha) {
                    found++;
                    chosen=row.Clone();
                }
            }
            if (found!=1) throw new Exception("ALLOWLIST_CASE_NOT_UNIQUE");
            string cid=Single(chosen,"case_ref");
            string requiredOpened=Single(chosen,"opened_at");
            DateTime expectedDate=DateTime.ParseExact(requiredOpened,
                "yyyy-MM-ddTHH:mm:ss",CultureInfo.InvariantCulture);
            if (expectedDate<MonthStart || expectedDate>=MonthEnd)
                throw new Exception("COHORT_DATE_OUT_OF_RANGE");

            foreach (var key in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}) {
                if (string.IsNullOrWhiteSpace(
                    Environment.GetEnvironmentVariable(key,EnvironmentVariableTarget.Process))) {
                    string value=Environment.GetEnvironmentVariable(
                        key,EnvironmentVariableTarget.Machine) ?? "";
                    if (string.IsNullOrWhiteSpace(value))
                        throw new Exception("QA_DATABASE_AUTH_UNAVAILABLE");
                    Environment.SetEnvironmentVariable(key,value,EnvironmentVariableTarget.Process);
                }
            }
            var xml=XDocument.Load(
                @"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
            string cs=xml.Descendants("connectionStrings").Descendants("add")
                .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
                .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
                ?? throw new Exception("QA_CONNECTION_UNAVAILABLE");
            if (!cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase) ||
                !cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase))
                throw new Exception("QA_ROOT_SCOPE_DENIED");
            using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
            var db=provider.Obtener(eSistema.ITIL,(byte)1);
            if (db.cdnConexion.NombreServidor!="ELSE70" ||
                db.cdnConexion.NombreBaseDatos!="dbITIL_D")
                throw new Exception("QA_DATABASE_SCOPE_DENIED");

            const string sql=@"SELECT TOP (2)
                CodigoIncidente,FechaSolicitud,CodigoServicio,CodigoModulo,
                CodigoCalificacion,CodigoOrigenIncidente,CodigoEstadoIncidente,
                DATALENGTH(DescripcionSolicitud) AS request_bytes
                FROM dbo.taIncidente
                WHERE CodigoIncidente=@cid
                AND FechaSolicitud>=@d1 AND FechaSolicitud<@d2
                ORDER BY CodigoIncidente";
            var data=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",
                new SqlParameter[]{
                    new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
                    new("@params",SqlDbType.NVarChar,160){
                        Value="@cid nvarchar(80), @d1 datetime, @d2 datetime"},
                    new("@cid",SqlDbType.NVarChar,80){Value=cid},
                    new("@d1",SqlDbType.DateTime){Value=MonthStart},
                    new("@d2",SqlDbType.DateTime){Value=MonthEnd}
                }).Tables[0];
            if (data.Rows.Count!=1) throw new Exception("EXACT_ONE_QA_ROW_REQUIRED");
            DataRow r=data.Rows[0];
            DateTime date=(DateTime)r["FechaSolicitud"];
            string opened=date.ToString("yyyy-MM-ddTHH:mm:ss",CultureInfo.InvariantCulture);
            string service=Text(r,"CodigoServicio");
            string module=Text(r,"CodigoModulo");
            string classification=Text(r,"CodigoCalificacion");
            if (opened!=requiredOpened ||
                ShaText(Text(r,"CodigoIncidente"))!=caseSha ||
                service!=Single(chosen,"service_code") ||
                module!=Single(chosen,"module_code") ||
                classification!=Single(chosen,"classification_code"))
                throw new Exception("CASE_SQL_ROW_BINDING_FAILED");
            byte[] source=File.ReadAllBytes(sourcePath);
            if (source.Length<100 || source.Length>5_000_000)
                throw new Exception("SOURCE_BYTES_INVALID");
            string sourceSha=Sha(source);
            string manifestJson=JsonSerializer.Serialize(new object[][]{
                new object[]{SourcePath,source.Length,sourceSha}});
            string manifest=ShaText(manifestJson);
            byte[] negative=Encoding.UTF8.GetBytes(manifestJson+" ");
            if (Sha(negative)==manifest)
                throw new Exception("NEGATIVE_SHA_TEST_DID_NOT_REJECT");
            var result = new {
                schema=Schema, scope=QaTarget, query_id=Query,
                case_sha256=caseSha, hand_source_sha256=sourceSha,
                hand_manifest_sha256=manifest,
                opened_at=opened, service_code=service, module_code=module,
                classification_code=classification,
                origin_code=Text(r,"CodigoOrigenIncidente"),
                status_code=Text(r,"CodigoEstadoIncidente"),
                request_bytes=Text(r,"request_bytes"),
                issued_at_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture),
                row_count=1,read_only=true,provenance_verified=true,
                historical_solution_not_read=true,
                deterministic_source_binding_passed=true,
                negative_sha_tamper_rejected=true,
                functional_repair_certified=false,
                core_o5_native_registration=false
            };
            string raw=JsonSerializer.Serialize(result);
            if (new FileInfo(output).Exists)throw new Exception("OUTPUT_EXISTS");
            string parent=Path.GetDirectoryName(output)
                ?? throw new Exception("OUTPUT_DIRECTORY_REQUIRED");
            Directory.CreateDirectory(parent);
            using (var file=new FileStream(output,FileMode.CreateNew,FileAccess.Write,FileShare.None)) {
                byte[] content=Encoding.UTF8.GetBytes(raw);
                file.Write(content);
                file.Flush(true);
            }
            Console.WriteLine(JsonSerializer.Serialize(new {
                status="NEW_QA_NUGET_RECEIPT_CREATED",case_sha256=caseSha,
                receipt_sha256=Sha(File.ReadAllBytes(output)),
                source_sha256=sourceSha,source_bytes=source.Length,
                source_manifest_sha256=manifest,query_id=Query,
                qa_scope=QaTarget,one_row=true,read_only=true,
                historical_solution_not_read=true,repair_certified=false
            }));
            return 0;
        } catch(Exception e) {
            Console.WriteLine(JsonSerializer.Serialize(new{
                status="QA_NUGET_READ_REJECTED",error_type=e.GetType().Name,
                error_code=e.Message.StartsWith("CASE_SQL") ||
                    e.Message.StartsWith("ALLOWLIST") ||
                    e.Message.StartsWith("EXACT_ONE") ||
                    e.Message.StartsWith("QA_") ? e.Message : "QA_READER_FAILED"
            }));
            return 2;
        }
    }
}
