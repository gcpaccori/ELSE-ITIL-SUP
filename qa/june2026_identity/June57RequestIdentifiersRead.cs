using System;
using System.Data;
using System.Data.SqlClient;
using System.Collections.Generic;
using System.Linq;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using SIELSEAccesoDatos;

// Signed, READ-ONLY, request-only recovery from original June 2026 ITIL.
// Never retrieves DescripcionSolucion or feeds historical golden notes
// into a candidate extractor. This is an exploratory 57-case posthoc cohort.
internal static class June57RequestIdentifiersRead {
 const string Root=@"C:\Temp\ELSE_ITIL_JUNE57_IDENTIFIER_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string ManifestSchema="else.itil.qa.2026-june57-source-and-history-reference-selection.v1";
 const string ManifestProof="else.itil.qa.2026-june57-source-and-history-reference-hmac.v1";
 const string Schema="else.itil.qa.2026-june57-request-identity-candidates.v1";
 const string Proof="else.itil.qa.2026-june57-request-identity-candidates-hmac.v1";
 const string FileName="June57RequestIdentifiersRead.cs";
 static readonly Dictionary<string,string> Patterns=new(){
  {"OT_EXACT",@"(?<!\w)(?:CodigoOrdenTrabajo|codigo\s+(?:de\s+)?orden\s+de\s+trabajo)\s*[:=#\s]{0,12}(\d{8,19})(?!\d)"},
  {"OT_CONTEXT",@"(?<!\w)(?:OT|O[. ]?T[.]?|orden\s+de\s+trabajo|Nro\s+OT)\s*(?:N[°ºo.]?\s*)?[:#=\s-]{0,12}(\d{8,19})(?!\d)"},
  {"COBRANZA_EXACT",@"(?<!\w)(?:CodigoCobranza|codigo\s+de\s+cobranza)\s*[:=#\s]{0,12}(\d{8,19})(?!\d)"},
  {"COBRANZA_CONTEXT",@"(?<!\w)(?:cobranza)\s*(?:n[uú]mero|Nro|N[°ºo.]?)?\s*[:=#\s-]{0,12}(\d{8,19})(?!\d)"},
  {"SUMINISTRO_EXACT",@"(?<!\w)(?:CodigoSuministro|c[oó]digo\s+(?:de\s+)?suministro|n[uú]mero\s+de\s+suministro)\s*[:=#\s]{0,12}(\d{5,16})(?!\d)"},
  {"SUMINISTRO_CONTEXT",@"(?<!\w)(?:suministro|NIS)\s*(?:N[°ºo.]?\s*)?[:#=\s-]{0,12}(\d{5,16})(?!\d)"},
  {"CAJA_EXACT",@"(?<!\w)(?:CodigoCaja|c[oó]digo\s+(?:de\s+)?caja)\s*[:=#\s]{0,12}(\d{1,8})(?!\d)"},
  {"CAJA_CONTEXT",@"(?<!\w)caja\s*(?:n[uú]mero|nro|N[°ºo.]?)?\s*[:#=\s-]{0,12}(\d{1,8})(?!\d)"},
  {"MEDIDOR_CONTEXT",@"(?<!\w)(?:medidor|CodigoMedidor|N[oú]mero\s+de\s+medidor)\s*(?:N[°ºo.]?\s*)?[:#=\s-]{0,12}(\d{5,17})(?!\d)"},
  {"COMPROBANTE_CONTEXT",@"(?<!\w)(?:comprobante|recibo|boleta|factura)\s*(?:N[°ºo.]?\s*)?[:#=\s-]{0,12}(\d{5,19})(?!\d)"}
 };
 static string Hash(byte[] raw)=>Convert.ToHexString(SHA256.HashData(raw)).ToLowerInvariant();
 static string Hash(string s)=>Hash(Encoding.UTF8.GetBytes(s));
 static void Need(bool b,string e){if(!b)throw new Exception(e);}
 static string Str(DataRow d,string name)=>d.IsNull(name)?"":Convert.ToString(d[name],CultureInfo.InvariantCulture)??"";
 static DataTable Q(AccesoDatos db,string sql,string signature,params SqlParameter[] args) {
   var ps=new List<SqlParameter>{
     new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
     new("@params",SqlDbType.NVarChar,100){Value=signature}
   };
   ps.AddRange(args);
   var ds=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",ps.ToArray());
   Need(ds!=null&&ds.Tables.Count>0,"REQUEST_IDENTITIES_SQL_RESULT_MISSING");
   return ds!.Tables[0];
 }
 static IEnumerable<object> Find(string raw,string field) {
   // Read only IDs adjacent to recognizable *business* labels. Never
   // persist generic numbers, DNI, phones, salary, account or address IDs.
   foreach(var pattern in Patterns) {
     foreach(Match match in Regex.Matches(raw,pattern.Value,RegexOptions.IgnoreCase|RegexOptions.CultureInvariant)) {
       var val=match.Groups[1].Value;
       if(!Regex.IsMatch(val,@"^\d{1,19}$"))continue;
       if(long.TryParse(val,NumberStyles.None,CultureInfo.InvariantCulture,out _) &&
         ((val.Length>1&&val.StartsWith("0",StringComparison.Ordinal))==false)) {
         yield return new{
           kind=pattern.Key,source_field=field,value_private=val,
           value_sha256=Hash(val),digit_length=val.Length,
           anchor_offset=match.Index,anchor_match_sha256=Hash(match.Value),
           historical_note_read=false
         };
       }
     }
   }
 }
 static void Main() {
   Directory.CreateDirectory(Root);
   foreach(string name in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}) {
     if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(name))) {
       var v=Environment.GetEnvironmentVariable(name,EnvironmentVariableTarget.Machine);
       Need(!string.IsNullOrWhiteSpace(v),"REQUEST_IDENTITIES_CORPORATE_ENV_MISSING");
       Environment.SetEnvironmentVariable(name,v);
     }
   }
   byte[] key=File.ReadAllBytes(Signer);Need(key.Length==32,"REQUEST_IDENTITIES_HMAC_SIGNER_MISSING");
   byte[] manRaw=File.ReadAllBytes(Path.Combine(Root,"june57_manifest.private.json"));
   using var man=JsonDocument.Parse(manRaw);
   using var pp=JsonDocument.Parse(File.ReadAllBytes(Path.Combine(Root,"june57_manifest.private.json.proof.json")));
   var selection=man.RootElement;
   string manifestSha=Hash(manRaw),sourceCodeSha=selection.GetProperty("source_sha256").GetString()??"";
   string mac=Convert.ToHexString(HMACSHA256.HashData(key,
      Encoding.UTF8.GetBytes(ManifestSchema+":"+sourceCodeSha+":"+manifestSha))).ToLowerInvariant();
   Need(selection.GetProperty("schema").GetString()==ManifestSchema
       &&pp.RootElement.GetProperty("schema").GetString()==ManifestProof
       &&pp.RootElement.GetProperty("receipt_sha256").GetString()==manifestSha
       &&pp.RootElement.GetProperty("hmac_sha256").GetString()==mac,
       "REQUEST_IDENTITIES_MANIFEST_NOT_SIGNED");
   var authorized=selection.GetProperty("rows").EnumerateArray().ToArray();
   var ranks=authorized.Select(x=>x.GetProperty("rank").GetInt32()).ToArray();
   Need(authorized.Length==57&&ranks.SequenceEqual(ranks.OrderBy(x=>x))
      &&ranks.Distinct().Count()==57,"REQUEST_IDENTITIES_COHORT_WRONG");
   var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string root=xml.Descendants("connectionStrings").Descendants("add")
     .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
     .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
      ??throw new Exception("REQUEST_IDENTITIES_ROOT_NOT_FOUND");
   Need(root.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)&&
     root.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"REQUEST_IDENTITIES_WRONG_ROOT");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(root));
   var itil=provider.Obtener(eSistema.ITIL,(byte)1);
   Need(itil.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
      &&itil.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase),
      "REQUEST_IDENTITIES_WRONG_DB");
   var sql=$@"WITH C AS (
     SELECT ROW_NUMBER() OVER (ORDER BY FechaSolicitud DESC,CodigoIncidente DESC) AS rank,
       CodigoIncidente,CodigoEmpresa,CodigoSucursal,CodigoModulo,CodigoServicio,
       FechaSolicitud,DescripcionSolicitud,DescripcionSolicitudRT
     FROM dbo.taIncidente
     WHERE FechaSolicitud>=@start AND FechaSolicitud<@end)
     SELECT * FROM C WHERE rank IN ({string.Join(",",ranks)}) ORDER BY rank";
   DataTable rows=Q(itil,sql,"@start datetime,@end datetime",
      new("@start",SqlDbType.DateTime){Value=new DateTime(2026,6,1)},
      new("@end",SqlDbType.DateTime){Value=new DateTime(2026,7,1)});
   Need(rows.Rows.Count==57,"REQUEST_IDENTITIES_QA_NOT_FIFTY_SEVEN");
   var objects=new List<object>();
   int plainCount=0,rtCount=0,primaryCandidateCases=0;
   foreach(DataRow row in rows.Rows) {
     int rank=Convert.ToInt32(row["rank"],CultureInfo.InvariantCulture);
     var expected=authorized[Array.IndexOf(ranks,rank)];
     string request=Str(row,"DescripcionSolicitud");
     string requestRt=Str(row,"DescripcionSolicitudRT");
     string caseSha=Hash(Str(row,"CodigoIncidente"));
     Need(expected.GetProperty("case_sha256").GetString()==caseSha
       &&expected.GetProperty("request_sha256").GetString()==Hash(request)
       &&expected.GetProperty("itil_company").GetString()==Str(row,"CodigoEmpresa")
       &&expected.GetProperty("module_code").GetString()==Str(row,"CodigoModulo").TrimEnd(),
       "REQUEST_IDENTITIES_CASE_OR_SOURCE_WRONG");
     string category=expected.GetProperty("category").GetString()??"";
     var candidates=Find(request,"PLAIN_REQUEST").Concat(Find(requestRt,"RICH_TEXT_REQUEST")).ToArray();
     var unique=new HashSet<string>();
     foreach(var c in candidates) {
        var e=JsonSerializer.SerializeToElement(c);
        unique.Add(e.GetProperty("kind").GetString()+":"+e.GetProperty("value_sha256").GetString());
     }
     bool primary=candidates.Any(c=>{
       var e=JsonSerializer.SerializeToElement(c);
       string kind=e.GetProperty("kind").GetString()??"";
       return category=="OT"?kind.StartsWith("OT_"):kind.StartsWith("COBRANZA_");
     });
     plainCount+=request.Length>0?1:0;
     rtCount+=requestRt.Length>0?1:0;
     primaryCandidateCases+=primary?1:0;
     objects.Add(new {
       rank,case_sha256=caseSha,category,
       module_code=Str(row,"CodigoModulo").TrimEnd(),
       itil_company=Str(row,"CodigoEmpresa"),
       itil_branch=Str(row,"CodigoSucursal"),
       itil_service=Str(row,"CodigoServicio"),
       request_sha256=Hash(request),
       request_rt_sha256=Hash(requestRt),
       plain_chars=request.Length,rich_text_chars=requestRt.Length,
       raw_plain_number_count=Regex.Matches(request,@"(?<!\d)\d{2,19}(?!\d)").Count,
       raw_rt_number_count=Regex.Matches(requestRt,@"(?<!\d)\d{2,19}(?!\d)").Count,
       plain_number_lengths=Regex.Matches(request,@"(?<!\d)\d{2,19}(?!\d)")
         .Cast<Match>().GroupBy(x=>x.Value.Length).ToDictionary(x=>x.Key,x=>x.Count()),
       rt_number_lengths=Regex.Matches(requestRt,@"(?<!\d)\d{2,19}(?!\d)")
         .Cast<Match>().GroupBy(x=>x.Value.Length).ToDictionary(x=>x.Key,x=>x.Count()),
       candidate_count=candidates.Length,distinct_kind_value_pairs=unique.Count,
       business_primary_candidate_present=primary,
       candidates,only_request_fields_read=true
     });
   }
   string sourceSha=Hash(File.ReadAllBytes(Path.Combine(Root,FileName)));
   var receipt=new {
     schema=Schema,source_sha256=sourceSha,
     original_june57_manifest_sha256=manifestSha,
     company="ITIL_ORIGINAL_57",
     qa="ELSE70/dbITIL_D",
     cohort_count=57,
     nonempty_plain=plainCount,
     nonempty_rich_text=rtCount,
     primary_candidate_cases=primaryCandidateCases,
     rows=objects,
     historical_note_column_selected=false,
     read_only=true,business_writes=0
   };
   byte[] bytes=JsonSerializer.SerializeToUtf8Bytes(receipt);
   string digest=Hash(bytes);
   string outpath=Path.Combine(Root,"june57_request_ids.private.json");
   File.WriteAllBytes(outpath,bytes);
   File.WriteAllBytes(outpath+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
     schema=Proof,source_sha256=sourceSha,receipt_sha256=digest,
     hmac_sha256=Convert.ToHexString(HMACSHA256.HashData(key,
       Encoding.UTF8.GetBytes(Schema+":"+sourceSha+":"+digest))).ToLowerInvariant(),
     read_only=true
   }));
   Console.WriteLine(JsonSerializer.Serialize(new{
     status="REQUEST_ONLY_57_SQL_PASS",nonempty_plain=plainCount,
     nonempty_rich_text=rtCount,primary_candidate_cases=primaryCandidateCases,
     total_candidates=objects.Sum(x=>JsonSerializer.SerializeToElement(x).GetProperty("candidate_count").GetInt32()),
     receipt_sha256=digest,business_writes=0}));
 }
}
