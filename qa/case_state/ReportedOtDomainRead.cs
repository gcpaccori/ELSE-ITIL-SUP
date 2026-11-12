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

// Optional domain-evidence probe: a UNIQUE explicit OT identifier mentioned
// verbatim in the text of a SIGNED ITIL case is queried on Distribucion QA.
// This is NOT an officially verified ITIL↔OT foreign-key relationship.
// Zero rows do NOT establish a missing order outside the probed table.
internal static class ReportedOtDomainRead {
 const string Root=@"C:\Temp\ELSE_ITIL_CASESTATE_QA_20261112";
 const string Original=@"C:\Temp\ELSE_ITIL_MONTHEND2026_QA_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.2026-reported-ot-domain-field-probe.v1";
 const string ProofSchema="else.itil.qa.2026-reported-ot-domain-hmac.v1";
 const string SourceSchema="else.itil.qa.2026-monthend100-source.v1";
 const string Target="ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo";
 static readonly Regex ExplicitOt=new(
   @"(?i)\b(?:OT|orden(?:es)?\s+de\s+trabajo)\s*(?:nro\.?|n°|nº|n\.|#|:|-)?\s*(\d{5,19})\b",
   RegexOptions.Compiled|RegexOptions.CultureInvariant);
 static string Hash(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
 static string Sha(string s)=>Hash(Encoding.UTF8.GetBytes(s));
 static string Val(DataRow row,string k)=>row.IsNull(k)?"":Convert.ToString(row[k],CultureInfo.InvariantCulture)??"";
 static void Need(bool pass,string code){if(!pass)throw new Exception(code);}
 static string Mac(string schema,string source,string receipt,byte[] key)=>
   Convert.ToHexString(HMACSHA256.HashData(key,
     Encoding.UTF8.GetBytes(schema+":"+source+":"+receipt))).ToLowerInvariant();
 static DataTable Q(AccesoDatos db,string sql,SqlParameter[] ps,string format){
    var args=new List<SqlParameter>{
      new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
      new("@params",SqlDbType.NVarChar,110){Value=format}
    };
    args.AddRange(ps);
    return db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args.ToArray()).Tables[0];
 }
 static (JsonDocument,string) SignedCohort(string ym,byte[] key,string originalSha){
    var path=Path.Combine(Original,"monthend_"+ym+".private.json");
    var body=File.ReadAllBytes(path);
    var data=JsonDocument.Parse(body);
    var proof=JsonDocument.Parse(File.ReadAllBytes(path+".proof.json"));
    var d=data.RootElement;
    string source=d.GetProperty("source_sha256").GetString()??"";
    string digest=Hash(body);
    Need(source==originalSha,"SOURCE_FILE_SHA_INVALID");
    Need(d.GetProperty("schema").GetString()==SourceSchema,"SOURCE_SCHEMA_INVALID");
    Need(d.GetProperty("selected").GetInt32()==100,"NOT_100_SOURCE_CASES");
    Need(!d.GetProperty("history_or_resolution_read").GetBoolean(),"SOURCE_GOLD_EXPOSED");
    Need(source==proof.RootElement.GetProperty("source_sha256").GetString() &&
       digest==proof.RootElement.GetProperty("receipt_sha256").GetString() &&
       Mac(SourceSchema,source,digest,key)==proof.RootElement.GetProperty("hmac_sha256").GetString(),
       "SOURCE_HMAC_MISMATCH");
    return (data,digest);
 }
 static int Main() {
  try {
   Directory.CreateDirectory(Root);
   foreach(var k in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
      if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(k))){
        var v=Environment.GetEnvironmentVariable(k,EnvironmentVariableTarget.Machine);
        Need(!string.IsNullOrWhiteSpace(v),"QA_CONNECTOR_CONFIG_MISSING");
        Environment.SetEnvironmentVariable(k,v);
      }
   }
   var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string cs=xml.Descendants("connectionStrings").Descendants("add")
      .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
      .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
      ??throw new Exception("QA_ROOT_CONNECTION_MISSING");
   Need(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)&&
       cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),
       "QA_ROOT_NOT_ALLOWED");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
   var itil=provider.Obtener(eSistema.ITIL,(byte)1);
   var distr=provider.Obtener(eSistema.Distribucion,(byte)1);
   Need(itil.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)&&
        itil.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase),
        "QA_ITIL_ROUTE_BAD");
   Need(distr.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)&&
        distr.cdnConexion.NombreBaseDatos.Equals("dbDistribucion_D",StringComparison.OrdinalIgnoreCase),
        "QA_DISTR_ROUTE_BAD");
   byte[] key=File.ReadAllBytes(Signer);
   Need(key.Length==32,"QA_SIGNER_INVALID");
   string sourceSha=Hash(File.ReadAllBytes(Path.Combine(Root,"ReportedOtDomainRead.cs")));
   string monthSourceSha=Hash(File.ReadAllBytes(Path.Combine(Original,"MonthEnd100Read.cs")));
   const string itilSql=@"SELECT TOP(100) CodigoIncidente,FechaSolicitud,CodigoModulo,
          CodigoEmpresa,DescripcionSolicitud
          FROM dbo.taIncidente
          WHERE FechaSolicitud>=@start AND FechaSolicitud<@end
          ORDER BY FechaSolicitud DESC,CodigoIncidente DESC";
   const string domainSql=@"SELECT TOP (2)
          CodigoOrdenTrabajo,CodigoEstadoOrdenTrabajo,
          CodigoClaseOrdenTrabajo,CodigoTipoOrdenTrabajo,
          CodigoSubTipoOrdenTrabajo,FechaElaboracion,FechaInicio,FechaFin
          FROM dbo.taOrdenTrabajo WHERE CodigoOrdenTrabajo=@ot";
   var samples=new List<object>();
   var cohorts=new List<object>();
   int unique=0,found=0,empty=0,ambiguous=0,noCode=0,otherCompany=0;
   for(int month=1;month<=9;month++){
      string ym="2026"+month.ToString("00",CultureInfo.InvariantCulture);
      DateTime start=new(2026,month,1),end=start.AddMonths(1);
      var (signed,cohortHash)=SignedCohort(ym,key,monthSourceSha);
      var selected=signed.RootElement.GetProperty("results");
      var rows=Q(itil,itilSql,new SqlParameter[]{
          new("@start",SqlDbType.DateTime){Value=start},
          new("@end",SqlDbType.DateTime){Value=end}
        },"@start datetime,@end datetime");
      Need(rows.Rows.Count==100,"ITIL_COHORT_DRIFT");
      cohorts.Add(new{month=ym[..4]+"-"+ym[4..],month_receipt_sha256=cohortHash});
      for(int n=0;n<100;n++){
         var row=rows.Rows[n];
         var signedRow=selected[n];
         string id=Val(row,"CodigoIncidente");
         string caseSha=Sha(id);
         Need(caseSha==signedRow.GetProperty("case_sha256").GetString() &&
              Val(row,"CodigoModulo").TrimEnd()==signedRow.GetProperty("module_code").GetString() &&
              Val(row,"CodigoEmpresa")==signedRow.GetProperty("company").GetString(),
              "REPORTED_OT_CASE_COHORT_NOT_BOUND");
         string company=Val(row,"CodigoEmpresa");
         var options=ExplicitOt.Matches(Val(row,"DescripcionSolicitud"))
               .Select(m=>m.Groups[1].Value).Distinct(StringComparer.Ordinal).ToList();
         if(options.Count==0){noCode++;continue;}
         if(options.Count!=1){ambiguous++;continue;}
         if(company!="1"){otherCompany++;continue;}
         string ot=options[0];
         unique++;
         var domain=Q(distr,domainSql,new SqlParameter[]{
           new("@ot",SqlDbType.VarChar,19){Value=ot}
         },"@ot varchar(19)");
         Need(domain.Rows.Count<=1,"DOMAIN_OT_NOT_UNIQUE");
         bool exists=domain.Rows.Count==1;
         if(exists)found++;else empty++;
         var item=exists?domain.Rows[0]:null;
         string code=exists?Val(item!,"CodigoOrdenTrabajo"):"";
         Need(!exists||code==ot,"DOMAIN_RETURNED_ANOTHER_OT");
         samples.Add(new{
            month=ym[..4]+"-"+ym[4..],rank=n+1,
            case_sha256=caseSha,
            reported_ot_sha256=Sha(ot),
            original_month_receipt_sha256=cohortHash,
            candidate_source="EXPLICIT_REPORTER_OT_IDENTIFIER_NOT_OFFICIAL_ITIL_FK",
            source=Target,query_id="QA_DISTR_OPERATIONAL_OT_BY_REPORTED_CODE",
            row_count=domain.Rows.Count,
            observed_fields=exists?(object)new{
               CodigoEstadoOrdenTrabajo=Val(item!,"CodigoEstadoOrdenTrabajo"),
               CodigoClaseOrdenTrabajo=Val(item!,"CodigoClaseOrdenTrabajo"),
               CodigoTipoOrdenTrabajo=Val(item!,"CodigoTipoOrdenTrabajo"),
               CodigoSubTipoOrdenTrabajo=Val(item!,"CodigoSubTipoOrdenTrabajo"),
               FechaElaboracion_present=!item!.IsNull("FechaElaboracion"),
               FechaInicio_present=!item!.IsNull("FechaInicio"),
               FechaFin_present=!item!.IsNull("FechaFin")
             }:null,
            read_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture),
            official_itil_ot_join_verified=false,
            causal_correction_certified=false,
            read_only=true,modifications=0
         });
      }
      signed.Dispose();
   }
   Need(unique==samples.Count&&unique==found+empty,"CANDIDATES_AND_DOMAIN_READS_MISMATCH");
   var receipt=new{
       schema=Schema,source_sha256=sourceSha,worker="ELSE62",
       qa_server="ELSE70",source=Target,
       scanned_itil_cases=900,
       candidates_reported_ot_unique=unique,
       candidates_ambiguous=ambiguous,
       candidates_other_company=otherCompany,
       no_explicit_unique_ot=noCode,
       exact_domain_record_found=found,
       exact_domain_record_empty=empty,
       domain_read_results=samples,
       month_receipts=cohorts,
       read_only=true,modifications=0,
       official_ticket_to_ot_fk_verified=false,
       read_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture)
   };
   byte[] body=JsonSerializer.SerializeToUtf8Bytes(receipt);
   string path=Path.Combine(Root,"reported_ot_domain.private.json");
   File.WriteAllBytes(path,body);
   string proofSha=Hash(body);
   File.WriteAllBytes(path+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
      schema=ProofSchema,source_sha256=sourceSha,receipt_sha256=proofSha,
      hmac_sha256=Mac(Schema,sourceSha,proofSha,key),read_only=true,worker="ELSE62"
   }));
   Console.WriteLine(JsonSerializer.Serialize(new{
      status="REPORTED_OT_DOMAIN_READ_COMPLETE",scan=900,
      unique,ambiguous,otherCompany,noCode,found,empty,
      domain_link_certified=0,modifications=0,
      receipt_sha256=proofSha
   }));
   return 0;
  }catch(Exception e){
    Console.Error.WriteLine("REPORTED_OT_QA_FAILED:"+e.GetType().Name+":"+e.Message);
    return 3;
  }
 }
}
