// ELSE-ITIL Aug 2026 Company-Routed QA: fixed signed read-only joins.
// Trust anchor: CodigoEmpresa from ELSE70/dbITIL_D/dbo.taIncidente.
// Never accepts a target database, free SQL, or identity from an LLM.
// Does not read historical solutions and never writes corporate data.
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

internal static class CompanyRoutedIdentity {
  const string Delivery="else.itil.aug2026.qa.company-routed-delivery.v2";
  const string Receipt="else.itil.aug2026.qa.company-routed-receipt.v2";
  const string Observation="else.itil.aug2026.qa.company-routed-observation.v2";
  const string Root=@"C:\Temp\ELSE_ITIL_COMPANY_ROUTED_V2_20261111";
  const string CohortRoot=@"C:\Temp\ELSE_ITIL_AUG2026_QA_20261110";
  const string Original=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110";
  const string Holdout=@"C:\Temp\ELSE_ITIL_SUPPLY_HOLDOUT_QA_20261111";
  const string HoldoutSha="04692e7be5e59c70da825c9597ed3dd9787b51bdae7105160be6a9489386aee8";
  static readonly Regex Ot=new(
    @"(?:\bOT\b|orden\s+(?:de\s+)?trabajo|c[oó]digo\s*OT)\s*[:#=-]?\s*(\d{4,19})\b",
    RegexOptions.IgnoreCase|RegexOptions.CultureInvariant);
  static readonly Regex Supply=new(@"\bsuministro\s*[:#=-]?\s*(\d{4,19})\b",
    RegexOptions.IgnoreCase|RegexOptions.CultureInvariant);
  static string Hash(byte[] x)=>Convert.ToHexString(SHA256.HashData(x)).ToLowerInvariant();
  static string Hash(string x)=>Hash(Encoding.UTF8.GetBytes(x));
  static void Require(bool ok,string msg){if(!ok)throw new Exception(msg);}
  static string Field(DataRow row,string name)=>row.IsNull(name)?"":Convert.ToString(row[name],CultureInfo.InvariantCulture)??"";
  static string Prop(JsonElement e,string key)=>e.GetProperty(key).GetString()??"";
  static long Key(string value){
    Require(Regex.IsMatch(value,@"^[0-9]{4,19}$") &&
      long.TryParse(value,NumberStyles.None,CultureInfo.InvariantCulture,out long n) && n>0,
      "INVALID_TYPED_ID");
    return long.Parse(value,CultureInfo.InvariantCulture);
  }
  static DataTable Read(dynamic db,string sql,string parameters,params SqlParameter[] queryParams){
    var args=new List<SqlParameter>{
      new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
      new("@params",SqlDbType.NVarChar,240){Value=parameters}
    };
    args.AddRange(queryParams);
    return db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args.ToArray()).Tables[0];
  }
  static int Count(dynamic db,string table,string column,string value){
    // Table and column are private constants selected from the literal allowlist.
    string sql="SELECT TOP(2) 1 AS hit FROM "+table+" WHERE "+column+"=@id";
    var rows=Read(db,sql,"@id bigint",new SqlParameter("@id",SqlDbType.BigInt){Value=Key(value)});
    Require(rows.Rows.Count<=2,"QA_ROW_LIMIT_BREACH");
    return rows.Rows.Count;
  }
  static int CountLink(dynamic db,string ot,string supply){
    const string sql=@"SELECT TOP(2) 1 AS hit FROM dbo.taOrdenTrabajo
      WHERE CodigoOrdenTrabajo=@ot AND CodigoSuministro=@supply";
    var result=Read(db,sql,"@ot bigint,@supply bigint",
       new SqlParameter("@ot",SqlDbType.BigInt){Value=Key(ot)},
       new SqlParameter("@supply",SqlDbType.BigInt){Value=Key(supply)});
    Require(result.Rows.Count<=2,"QA_LINK_ROWS_UNBOUNDED");
    return result.Rows.Count;
  }
  static string[] Unique(Regex pattern,string text)=>
      pattern.Matches(text).Cast<Match>().Select(m=>m.Groups[1].Value)
        .Distinct(StringComparer.Ordinal).ToArray();
  static int Main(){
   try {
    foreach(string key in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
      if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(key))){
       var value=Environment.GetEnvironmentVariable(key,EnvironmentVariableTarget.Machine);
       Require(!string.IsNullOrWhiteSpace(value),"QA_ACCESS_NOT_PRESENT");
       Environment.SetEnvironmentVariable(key,value);
      }
    }
    var hmacKey=File.ReadAllBytes(Path.Combine(Original,"worker_hmac.private"));
    Require(hmacKey.Length==32,"HMAC_KEY_NOT_32_BYTES");
    string sourceSha=Hash(File.ReadAllBytes(Path.Combine(Root,"CompanyRoutedIdentity.cs")));
    byte[] cohortBytes=File.ReadAllBytes(Path.Combine(CohortRoot,"aug2026_blind_redacted.private.jsonl"));
    var manifest=JsonDocument.Parse(File.ReadAllBytes(Path.Combine(CohortRoot,"aug2026_manifest.json"))).RootElement;
    string blindSha=Prop(manifest,"blind_sha256");
    Require(blindSha==Hash(cohortBytes) &&
      manifest.GetProperty("cases").GetInt32()==1819 &&
      manifest.GetProperty("gold_shown_to_model").GetBoolean()==false,"AUG_COHORT_NOT_PINNED");
    var rows=new Dictionary<string,(string text,string rawSha)>(StringComparer.Ordinal);
    foreach(var rawLine in Encoding.UTF8.GetString(cohortBytes).Split('\n')){
      string line=rawLine.TrimEnd('\r');
      if(string.IsNullOrWhiteSpace(line))continue;
      using var parsed=JsonDocument.Parse(line);
      var row=parsed.RootElement;
      string sha=Prop(row,"ticket_sha256");
      Require(sha.Length==64 && !rows.ContainsKey(sha) &&
              Prop(row,"month")=="2026-08" &&
              Prop(row,"historical_resolution")=="WITHHELD","AUG_CASE_DRIFT");
      rows[sha]=(Prop(row,"incident_text_redacted"),Hash(line));
    }
    Require(rows.Count==1819,"COHORT_COUNT_DRIFT");
    var selected=new HashSet<string>(StringComparer.Ordinal);
    foreach(var reqPath in Directory.GetFiles(Path.Combine(Original,"requests"),"*.private.json")){
      using var req=JsonDocument.Parse(File.ReadAllBytes(reqPath));
      string sha=Prop(req.RootElement,"case_sha256");
      Require(rows.ContainsKey(sha) && Prop(req.RootElement,"cohort_sha256")==blindSha
             && selected.Add(sha),"OLD_JOB_NOT_AUTHORIZED");
    }
    Require(selected.Count==5,"NOT_EXACT_FIVE_OLD_OT_CASES");
    string sampleFile=Path.Combine(Holdout,"sample.private.json");
    var sampleBytes=File.ReadAllBytes(sampleFile);
    Require(Hash(sampleBytes)==HoldoutSha,"HOLDOUT_SAMPLE_NOT_PINNED");
    using(var sample=JsonDocument.Parse(sampleBytes)){
      var e=sample.RootElement;
      Require(Prop(e,"cohort_sha256")==blindSha &&
             e.GetProperty("selected").GetArrayLength()==10,"HOLDOUT_WRONG_COHORT");
      foreach(var entry in e.GetProperty("selected").EnumerateArray()){
        string sha=Prop(entry,"case_sha256");
        Require(rows.ContainsKey(sha) &&
                Prop(entry,"case_row_sha256")!="" &&
                selected.Add(sha),"HOLDOUT_CASE_NOT_UNIQUE");
      }
    }
    Require(selected.Count==15,"EXPECTED_FIFTEEN_CASES");
    var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
    string? cs=xml.Descendants("connectionStrings").Descendants("add")
        .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
        .Select(x=>(string?)x.Attribute("connectionString")).Single() ?? throw new Exception("QA_ROOT_MISSING");
    Require(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase) &&
            cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),
            "QA_ROOT_NOT_ALLOWED");
    using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
    var itil=provider.Obtener(eSistema.ITIL,(byte)1);
    Require(itil.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase) &&
            itil.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase),
            "QA_ITIL_TARGET_DRIFT");
    const string itilSql=@"SELECT CodigoIncidente,CodigoEmpresa,CodigoSucursal,
        CodigoServicio,CodigoSistema,CodigoModulo
      FROM dbo.taIncidente
      WHERE FechaSolicitud>=@start AND FechaSolicitud<@end";
    var dbRows=Read(itil,itilSql,"@start datetime,@end datetime",
      new("@start",SqlDbType.DateTime){Value=new DateTime(2026,8,1)},
      new("@end",SqlDbType.DateTime){Value=new DateTime(2026,9,1)});
    Require(dbRows.Rows.Count==1819,"ITIL_LIVE_COHORT_COUNT_CHANGED");
    var found=new Dictionary<string,DataRow>(StringComparer.Ordinal);
    foreach(DataRow row in dbRows.Rows){
      string sha=Hash(Field(row,"CodigoIncidente"));
      if(selected.Contains(sha))Require(found.TryAdd(sha,row),"ITIL_DUPLICATE_ID");
    }
    Require(found.Count==15,"NOT_ALL_CASES_IN_AUTHORITATIVE_ITIL");
    var outcomes=new List<object>();int queries=0;
    foreach(string sha in selected.OrderBy(s=>s,StringComparer.Ordinal)){
      var row=found[sha];
      string companyText=Field(row,"CodigoEmpresa");
      Require(companyText=="1" || companyText=="3","ITIL_COMPANY_NOT_ALLOWLISTED");
      byte company=byte.Parse(companyText,CultureInfo.InvariantCulture);
      string target=company==1?"dbComercial001_D":"dbComercial003_D";
      var db=provider.Obtener(eSistema.Comercial,company);
      Require(db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
          && db.cdnConexion.NombreBaseDatos.Equals(target,StringComparison.OrdinalIgnoreCase),
          "COMPANY_DB_PROVIDER_MISMATCH");
      string text=rows[sha].text;
      string[] ots=Unique(Ot,text),supplies=Unique(Supply,text);
      Require(ots.Length<=1 && supplies.Length<=1 &&
              (ots.Length==1 || supplies.Length==1),"TICKET_IDENTIFIER_AMBIGUOUS");
      string mode=ots.Length==1?"OT":"SUPPLY";
      string? ot=ots.Length==1?ots[0]:null;
      string? supply=supplies.Length==1?supplies[0]:null;
      var counts=new SortedDictionary<string,int>(StringComparer.Ordinal);
      if(mode=="OT"){
        counts["order"]=Count(db,"dbo.taOrdenTrabajo","CodigoOrdenTrabajo",ot!);queries++;
        counts["installation"]=Count(db,"dbo.taOTInstalacion","CodigoOrdenTrabajo",ot!);queries++;
        counts["interior"]=Count(db,"dbo.taOTInstalacionInterior","CodigoOrdenTrabajo",ot!);queries++;
        counts["meter"]=Count(db,"dbo.taOTServicioExtraordinarioInstalacionMedidor","CodigoOrdenTrabajo",ot!);queries++;
        if(supply!=null){
          counts["supply"]=Count(db,"dbo.taSuministro","CodigoSuministro",supply);queries++;
          counts["orders_by_supply"]=Count(db,"dbo.taOrdenTrabajo","CodigoSuministro",supply);queries++;
          counts["exact_ot_supply"]=CountLink(db,ot!,supply);queries++;
        }
      }else{
        counts["supply"]=Count(db,"dbo.taSuministro","CodigoSuministro",supply!);queries++;
        counts["orders_by_supply"]=Count(db,"dbo.taOrdenTrabajo","CodigoSuministro",supply!);queries++;
        counts["massive_installation"]=Count(db,"dbo.taInstalacionMasivaSuministro","CodigoSuministro",supply!);queries++;
        counts["installation_owner"]=Count(db,"dbo.taOTInstalacionPropietario","CodigoSuministro",supply!);queries++;
      }
      var receipt=new {
        schema=Receipt,case_sha256=sha,case_row_line_sha256=rows[sha].rawSha,
        blind_cohort_sha256=blindSha,
        itil_source="ELSE70/dbITIL_D/dbo.taIncidente",
        itil_company=company, itil_branch=Field(row,"CodigoSucursal"),
        itil_service=Field(row,"CodigoServicio"),
        itil_module=Field(row,"CodigoModulo"),
        itil_sistema=Field(row,"CodigoSistema"),
        itil_row_verified_from_corporate_sql=true,
        claim_type=mode,
        reported_ot_sha256=ot!=null?Hash(ot):null,
        reported_supply_sha256=supply!=null?Hash(supply):null,
        observation=new {
          schema=Observation,
          qa_target="ELSE70/"+target,
          sql_profile=mode=="OT"?"PINNED_TYPED_OT_SELECTS":"PINNED_TYPED_SUPPLY_SELECTS",
          counts,read_utc=DateTime.UtcNow.ToString("O"),
          read_only=true,changes_executed=false
        },
        historical_solution_read=false,corporate_itil_business_join_certified=false,
        root_cause_certified=false,repair_certified=false,
        source_sha256=sourceSha
      };
      byte[] receiptBytes=Encoding.UTF8.GetBytes(JsonSerializer.Serialize(receipt));
      string receiptSha=Hash(receiptBytes);
      string jobId=Hash(Delivery+":"+sha+":"+blindSha).Substring(0,32);
      string msg=Delivery+":"+jobId+":"+sourceSha+":"+receiptSha;
      string signature=Convert.ToHexString(HMACSHA256.HashData(hmacKey,
        Encoding.UTF8.GetBytes(msg))).ToLowerInvariant();
      var envelope=new {
        schema=Delivery,job_id=jobId,case_sha256=sha,blind_cohort_sha256=blindSha,
        source_sha256=sourceSha,sample_sha256=HoldoutSha,
        receipt_sha256=receiptSha,receipt_json_base64=Convert.ToBase64String(receiptBytes),
        hmac_sha256=signature,sql_executed_on_windows=true,
        read_only=true,changes_executed=false
      };
      string outFile=Path.Combine(Root,"outbox",jobId+".private.json");
      using(var stream=new FileStream(outFile,FileMode.CreateNew,FileAccess.Write,FileShare.None)){
        byte[] bytes=Encoding.UTF8.GetBytes(JsonSerializer.Serialize(envelope));
        stream.Write(bytes);
      }
      outcomes.Add(new {case_prefix=sha.Substring(0,12),company,mode,
        database=target,exact_hits=counts.Values.Sum(),
        result="SIGNED_READ_ONLY_QA_SCOPE_ONLY"});
    }
    Console.WriteLine(JsonSerializer.Serialize(new{
       schema="else.itil.aug2026.company-routed-qa-run.v2",
       cases=outcomes.Count,total_fixed_selects=queries,
       read_only=true,modified_business_rows=0,
       historical_solutions_read=false,
       results=outcomes,source_sha256=sourceSha
    }));
    return 0;
   }catch(Exception ex){
     Console.Error.WriteLine("COMPANY_ROUTED_QA_FAILED:"+ex.GetType().Name);
     return 3;
   }
  }
}

