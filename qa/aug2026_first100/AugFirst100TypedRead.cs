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

// SELECT-only first 100 August 2026; neither historical solutions nor writes are queried.
// A QA observation in November does NOT establish an August state or intervention.
internal static class AugFirst100TypedRead {
 const string OldRoot=@"C:\Temp\ELSE_ITIL_AUG2026_QA_20261110";
 const string Root=@"C:\Temp\ELSE_ITIL_AUG_TYPED100_V2_20261117";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.aug2026-first100-company-typed.v1";
 const string Reader="AugFirst100TypedRead.cs";
 static readonly string[] Databases={
  "dbComercial001_D","dbComercial003_D","dbComercial004_D",
  "dbComercial006_D","dbComercial007_D","dbComercial008_D",
  "dbComercial100_D","dbComercial200_D","dbComercial001_Diario",
  "dbComercial001_20230131","dbComercial003_mayo",
  "dbGerencial_D","dbDistribucion_D"};
 static readonly (string Kind,string Table,string Pk,string Pattern)[] TypedRules={
  ("SUPPLY","taSuministro","CodigoSuministro",
     @"(?<!\w)(?:CodigoSuministro|c[oó]digo\s+(?:de\s+)?suministro|n[uú]mero\s+de\s+suministro|suministro|NIS)\s*(?:n[°ºo.]?\s*)?[:#=\s-]{0,16}(\d{5,19})(?!\d)"),
  ("OT","taOrdenTrabajo","CodigoOrdenTrabajo",
     @"(?<!\w)(?:CodigoOrdenTrabajo|orden\s+(?:de\s+)?trabajo|OT)\s*(?:n[°ºo.]?\s*)?[:#=\s-]{0,16}(\d{8,19})(?!\d)"),
  ("COLLECTION","taCobranza","CodigoCobranza",
     @"(?<!\w)(?:CodigoCobranza|c[oó]digo\s+(?:de\s+)?cobranza|cobranza)\s*(?:n[°ºo.]?\s*)?[:#=\s-]{0,16}(\d{8,19})(?!\d)"),
  ("CLAIM","taReclamoComercial","CodigoReclamo",
     @"(?<!\w)(?:CodigoReclamo|c[oó]digo\s+(?:de\s+)?reclamo|reclamo)\s*(?:n[°ºo.]?\s*)?[:#=\s-]{0,16}(\d{5,19})(?!\d)"),
  ("METER","taMedidor","CodigoMedidor",
     @"(?<!\w)(?:CodigoMedidor|c[oó]digo\s+(?:de\s+)?medidor|medidor)\s*(?:n[°ºo.]?\s*)?[:#=\s-]{0,16}(\d{5,19})(?!\d)"),
  ("FISE_REQUEST","taSolicitudFISEBeneficiario","CodigoSolicitudFISEBeneficiario",
     @"(?<!\w)(?:CodigoSolicitudFISEBeneficiario|solicitud\s+FISE)\s*(?:n[°ºo.]?\s*)?[:#=\s-]{0,16}(\d{5,19})(?!\d)")
 };
 static string Hash(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
 static string Hash(string s)=>Hash(Encoding.UTF8.GetBytes(s));
 static string Val(DataRow r,string col)=>r.IsNull(col)?"":Convert.ToString(r[col],CultureInfo.InvariantCulture)??"";
 static void Need(bool b,string err) {if(!b) throw new InvalidOperationException(err);}
 static DataTable Exec(AccesoDatos db,string sql,string signature="", params SqlParameter[] parameters) {
   var p=new List<SqlParameter>{
      new("@stmt",SqlDbType.NVarChar,-1){Value=sql},
      new("@params",SqlDbType.NVarChar,-1){Value=signature}};
   p.AddRange(parameters);
   var rows=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",p.ToArray());
   Need(rows!=null && rows.Tables.Count>0,"QA_SQL_TABLE_MISSING");
   return rows!.Tables[0];
 }
 static void Main(){
   Directory.CreateDirectory(Root);
   foreach(var name in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
     if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(name))){
       var value=Environment.GetEnvironmentVariable(name,EnvironmentVariableTarget.Machine);
       Need(!string.IsNullOrWhiteSpace(value),"QA_ACCESS_CONFIG_NOT_FOUND");
       Environment.SetEnvironmentVariable(name,value);
     }
   }
   byte[] key=File.ReadAllBytes(Signer);
   Need(key.Length==32,"QA_RECEIPT_SIGNER_INVALID");
   string manifestFile=Path.Combine(OldRoot,"aug2026_manifest.json");
   using var manifestJson=JsonDocument.Parse(File.ReadAllBytes(manifestFile));
   var manifest=manifestJson.RootElement;
   var srcFile=Path.Combine(OldRoot,"aug2026_requests.private.jsonl");
   byte[] srcRaw=File.ReadAllBytes(srcFile);
   Need(manifest.GetProperty("source_sha256").GetString()==Hash(srcRaw)
      &&manifest.GetProperty("cases").GetInt32()==1819
      &&manifest.GetProperty("gold_shown_to_model").GetBoolean()==false
      &&manifest.GetProperty("corporate_db_scope").GetString()=="ELSE70/dbITIL_D/dbo.taIncidente",
      "AUGUST_FROZEN_SOURCE_MISMATCH");
   var originals=File.ReadAllLines(srcFile).Where(s=>!string.IsNullOrWhiteSpace(s)).ToArray();
   Need(originals.Length==1819,"AUGUST_ORIGINAL_COUNT_CHANGED");
   var frozen=new List<JsonElement>();
   for(int i=0;i<100;i++) frozen.Add(JsonDocument.Parse(originals[i]).RootElement.Clone());

   var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string config=xml.Descendants("connectionStrings").Descendants("add")
       .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
       .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()??throw new InvalidOperationException("QA_MISSING_CONNECTOR_ROOT");
   Need(config.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)
      &&config.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),
      "NOT_QA_CONNECTOR");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(config));
   var itil=provider.Obtener(eSistema.ITIL,(byte)1);
   var comm=provider.Obtener(eSistema.Comercial,(byte)1);
   Need(itil.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
      &&itil.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase)
      &&comm.cdnConexion.NombreBaseDatos.Equals("dbComercial001_D",StringComparison.OrdinalIgnoreCase),
      "UNEXPECTED_ITIL_OR_COMMERCE_DB");
   var rows=Exec(itil,@"SELECT TOP (100) CodigoIncidente,FechaSolicitud,CodigoEmpresa,
       CodigoSucursal,CodigoModulo,CodigoServicio,
       LEFT(CONVERT(nvarchar(max),DescripcionSolicitud),1800) AS request_text,
       LEFT(CONVERT(nvarchar(max),DescripcionSolicitud),12000) AS request_full
       FROM dbo.taIncidente
       WHERE FechaSolicitud>=@start AND FechaSolicitud<@end
       ORDER BY FechaSolicitud ASC,CodigoIncidente ASC",
       "@start datetime,@end datetime",
       new("@start",SqlDbType.DateTime){Value=new DateTime(2026,8,1)},
       new("@end",SqlDbType.DateTime){Value=new DateTime(2026,9,1)});
   Need(rows.Rows.Count==100,"AUG_FIRST100_SQL_COUNT_CHANGED");
   var byCandidate=new Dictionary<long,List<int>>();
   var byRank=new Dictionary<int,(string CaseSha,string Branch,string Module)>();
   var cases=new List<object>();
   // Only explicit typed source labels, extracted from raw original request on ELSE62.
   // A generic 19-digit number alone is NEVER sufficient for this new authority.
   var typedSources=new Dictionary<(int Rank,string Kind),HashSet<long>>();
   var sourceCompanies=new Dictionary<int,string>();
   var expandedRequestHashes=new Dictionary<int,string>();
   var caseKinds=new Dictionary<int,HashSet<(string Kind,string Pk)>>();
   int candidateTotal=0;
   for(int i=0;i<100;i++){
      var row=rows.Rows[i];
      var expected=frozen[i];
      string ticketSha=Hash(Val(row,"CodigoIncidente"));
      string req=Val(row,"request_text");
      string openedAt=((DateTime)row["FechaSolicitud"]).ToString("yyyy-MM-ddTHH:mm:ss",CultureInfo.InvariantCulture);
      string module=Val(row,"CodigoModulo");
      string service=Val(row,"CodigoServicio");
      Need(expected.GetProperty("case_sha256").GetString()==ticketSha, "AUG_CASE_ID_SHA_MISMATCH");
      Need(expected.GetProperty("opened_at").GetString()==openedAt, "AUG_CASE_DATE_MISMATCH");
      Need(expected.GetProperty("service_code").GetString()==service, "AUG_CASE_SERVICE_MISMATCH");
      Need(expected.GetProperty("module_code").GetString()==module, "AUG_CASE_MODULE_MISMATCH");
      Need(expected.GetProperty("incident_text").GetString()==req, "AUG_CASE_TEXT_MISMATCH");
      var candidates=new HashSet<long>();
      foreach(Match m in Regex.Matches(req,@"(?<!\d)\d{19}(?!\d)",RegexOptions.CultureInvariant)){
         if(long.TryParse(m.Value,NumberStyles.None,CultureInfo.InvariantCulture,out long v))
            candidates.Add(v);
      }
      Need(candidates.Count<=150,"AUG_FIRST100_TOO_MANY_NUMERIC_REFERENCES");
      candidateTotal+=candidates.Count;
      int rank=i+1;
      sourceCompanies[rank]=Val(row,"CodigoEmpresa");
      string expandedRequest=Val(row,"request_full");
      Need(expandedRequest.StartsWith(req,StringComparison.Ordinal),"EXPANDED_REQUEST_PREFIX_DRIFT");
      expandedRequestHashes[rank]=Hash(expandedRequest);
      foreach(var rule in TypedRules){
         var numbers=new HashSet<long>();
         foreach(Match hit in Regex.Matches(expandedRequest,rule.Pattern,
             RegexOptions.IgnoreCase|RegexOptions.CultureInvariant)){
            string value=hit.Groups[1].Value;
            if(value.Length>1 && value[0]=='0')continue;
            if(long.TryParse(value,NumberStyles.None,CultureInfo.InvariantCulture,
               out long number) && number>0)numbers.Add(number);
         }
         if(numbers.Count>0)typedSources[(rank,rule.Kind)]=numbers;
      }
      foreach(long num in candidates) {
          if(!byCandidate.TryGetValue(num,out var indices)) byCandidate[num]=indices=new();
          indices.Add(rank);
      }
      byRank[rank]=(ticketSha,Val(row,"CodigoSucursal"),module);
      caseKinds[rank]=new();
      cases.Add(new{
       rank,case_sha256=ticketSha,request_sha256=Hash(req),opened_at=openedAt,
       module_code=module,service_code=service,itil_company=Val(row,"CodigoEmpresa"),
       itil_branch=Val(row,"CodigoSucursal"),candidate_19_digit_count=candidates.Count,
       expanded_request_sha256=Hash(Val(row,"request_full")),
       source_only=true,history_not_read=true
      });
   }
   var online=Exec(comm,@"SELECT name FROM sys.databases
       WHERE state_desc='ONLINE' AND name IN(
       'dbComercial001_D','dbComercial003_D','dbComercial004_D',
       'dbComercial006_D','dbComercial007_D','dbComercial008_D',
       'dbComercial100_D','dbComercial200_D','dbComercial001_Diario',
       'dbComercial001_20230131','dbComercial003_mayo','dbGerencial_D','dbDistribucion_D')");
   Need(online.Rows.Count==13,"QA_REQUIRED_DB_NOT_VISIBLE");
   var matches=new List<object>();
   int reads=0;
   int sameBranchObservations=0,wrongBranchObservations=0;
   var seen=new HashSet<(int Rank,string Kind,string Db,long Pk)>();
   var candidatesAll=byCandidate.Keys.OrderBy(x=>x).ToArray();
   foreach(string db in Databases){
      var meta=Exec(comm,$@"SELECT t.name AS table_name,
        MAX(CASE WHEN c.name='CodigoSucursal' THEN 1 ELSE 0 END) AS has_branch
        FROM [{db}].sys.tables t JOIN [{db}].sys.schemas s ON s.schema_id=t.schema_id
        JOIN [{db}].sys.columns c ON c.object_id=t.object_id
        WHERE s.name='dbo' AND t.name IN('taOrdenTrabajo','taCobranza')
        GROUP BY t.name");
      var available=meta.Rows.Cast<DataRow>()
         .ToDictionary(x=>Val(x,"table_name"),x=>Val(x,"has_branch")=="1");
      foreach(string kind in new[]{"OT","COLLECTION"}){
         string table=kind=="OT"?"taOrdenTrabajo":"taCobranza";
         string pk=kind=="OT"?"CodigoOrdenTrabajo":"CodigoCobranza";
         if(!available.ContainsKey(table))continue;
         Need(available[table],"QA_CORPORATE_TABLE_NO_BRANCH_COLUMN");
         for(int j=0;j<candidatesAll.Length;j+=160){
            var chunk=candidatesAll.Skip(j).Take(160).ToArray();
            var sqlParams=chunk.Select((n,k)=>new SqlParameter("@p"+k,SqlDbType.BigInt){Value=n}).ToArray();
            var sql=$"SELECT {pk},CodigoSucursal FROM [{db}].dbo.{table} WHERE {pk} IN ("+
                    string.Join(",",sqlParams.Select(x=>x.ParameterName))+")";
            var data=Exec(comm,sql,string.Join(",",sqlParams.Select(x=>x.ParameterName+" bigint")),sqlParams);
            reads++;
            Need(data.Rows.Count<=chunk.Length,"QA_BUSINESS_PK_DUPLICATES");
            foreach(DataRow found in data.Rows){
               long val=Convert.ToInt64(found[pk],CultureInfo.InvariantCulture);
               Need(byCandidate.TryGetValue(val,out var ranks),"QA_BUSINESS_PK_NOT_REQUESTED");
               foreach(int rank in ranks!){
                  Need(seen.Add((rank,kind,db,val)),"QA_DUPLICATED_OBSERVATION");
                  bool branchSame=Val(found,"CodigoSucursal")==byRank[rank].Branch;
                  if(branchSame){
                    sameBranchObservations++;
                    caseKinds[rank].Add((kind,val.ToString(CultureInfo.InvariantCulture)));
                  } else wrongBranchObservations++;
                  matches.Add(new{
                   rank,case_sha256=byRank[rank].CaseSha,
                   kind,source_database=db,pk_sha256=Hash(val.ToString(CultureInfo.InvariantCulture)),
                   business_pk_private=val.ToString(CultureInfo.InvariantCulture),
                   business_branch=Val(found,"CodigoSucursal"),
                   itil_branch=byRank[rank].Branch,
                   same_branch=branchSame,
                   current_november_qa_only=true,history_not_read=true
                  });
               }
            }
         }
      }
   }
   // Independent typed pass. Company-scoped provider route is compulsory.
   // Generic 19-digit legacy matches above are preserved for comparison but
   // are NOT automatically promoted to a verified typed authority.
   var typedVerified=Enumerable.Range(1,100).ToDictionary(k=>k,k=>new HashSet<(string Kind,string PkSha)>());
   var typedMatches=new List<object>();
   var typedWrongRanks=new HashSet<int>();
   var typedMissingKinds=new HashSet<string>();
   var typedCompanies=new[]{(Company:"1",Id:(byte)1,Database:"dbComercial001_D"),
                             (Company:"3",Id:(byte)3,Database:"dbComercial003_D")};
   int typedSelects=0,typedWrong=0,typedSame=0;
   foreach(var companyRoute in typedCompanies){
      var selected=typedSources.Where(x=>sourceCompanies[x.Key.Rank]==companyRoute.Company).ToArray();
      if(selected.Length==0)continue;
      var business=provider.Obtener(eSistema.Comercial,companyRoute.Id);
      Need(business.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
        &&business.cdnConexion.NombreBaseDatos.Equals(companyRoute.Database,StringComparison.OrdinalIgnoreCase),
        "QA_TYPED_COMPANY_PROVIDER_MISMATCH");
      var meta=Exec(business,@"SELECT t.name AS table_name,c.name AS column_name
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.columns c ON c.object_id=t.object_id
        WHERE s.name='dbo' AND t.name IN('taSuministro','taOrdenTrabajo',
           'taCobranza','taReclamoComercial','taMedidor','taSolicitudFISEBeneficiario')
        AND c.name IN('CodigoSuministro','CodigoSucursal','CodigoOrdenTrabajo',
           'CodigoCobranza','CodigoReclamo','CodigoMedidor','CodigoSolicitudFISEBeneficiario')");
      var schema=meta.Rows.Cast<DataRow>().GroupBy(r=>Val(r,"table_name"))
         .ToDictionary(g=>g.Key,g=>g.Select(r=>Val(r,"column_name")).ToHashSet());
      foreach(var rule in TypedRules){
         var entries=selected.Where(x=>x.Key.Kind==rule.Kind).ToArray();
         if(entries.Length==0)continue;
         bool tableValid=schema.TryGetValue(rule.Table,out var columns)
             &&columns.Contains(rule.Pk)
             &&(rule.Kind=="METER" ? columns.Contains("CodigoSuministro")
                  &&schema.TryGetValue("taSuministro",out var supplyColumns)
                  &&supplyColumns.Contains("CodigoSuministro")
                  &&supplyColumns.Contains("CodigoSucursal")
                  : columns.Contains("CodigoSucursal"));
         if(!tableValid){typedMissingKinds.Add(rule.Kind);continue;}
         var numberRanks=new Dictionary<long,HashSet<int>>();
         foreach(var ent in entries)foreach(long number in ent.Value){
            if(!numberRanks.TryGetValue(number,out var ranks))
                numberRanks[number]=ranks=new();
            ranks.Add(ent.Key.Rank);
         }
         var numbers=numberRanks.Keys.OrderBy(x=>x).ToArray();
         Need(numbers.Length<=15000,"QA_TYPED_CANDIDATE_LIMIT");
         for(int offset=0;offset<numbers.Length;offset+=100){
            var chunk=numbers.Skip(offset).Take(100).ToArray();
            var parameters=chunk.Select((n,k)=>new SqlParameter("@n"+k,SqlDbType.BigInt){Value=n}).ToArray();
            string paramNames=string.Join(",",parameters.Select(x=>x.ParameterName));
            string sql=rule.Kind=="METER"
               ? "SELECT m.CodigoMedidor AS pk,s.CodigoSucursal FROM dbo.taMedidor m "+
                 "JOIN dbo.taSuministro s ON s.CodigoSuministro=m.CodigoSuministro "+
                 "WHERE m.CodigoMedidor IN ("+paramNames+")"
               : "SELECT "+rule.Pk+" AS pk,CodigoSucursal FROM dbo."+rule.Table+
                 " WHERE "+rule.Pk+" IN ("+paramNames+")";
            var hits=Exec(business,sql,string.Join(",",
                 parameters.Select(x=>x.ParameterName+" bigint")),parameters);
            typedSelects++;
            Need(hits.Rows.Count<=chunk.Length,"QA_TYPED_PK_DUPLICATE");
            foreach(DataRow hit in hits.Rows){
              long pk=Convert.ToInt64(hit["pk"],CultureInfo.InvariantCulture);
              Need(numberRanks.TryGetValue(pk,out var ranks),"QA_TYPED_PK_NOT_FROM_REQUEST");
              foreach(int rank in ranks!){
                bool branchSame=Val(hit,"CodigoSucursal")==byRank[rank].Branch;
                string pkSha=Hash(pk.ToString(CultureInfo.InvariantCulture));
                if(branchSame){typedVerified[rank].Add((rule.Kind,pkSha));typedSame++;}
                else{typedWrongRanks.Add(rank);typedWrong++;}
                typedMatches.Add(new {
                   rank,case_sha256=byRank[rank].CaseSha,
                   business_kind=rule.Kind,company=companyRoute.Company,
                   qa_database=companyRoute.Database,
                   pk_sha256=pkSha,branch_matches=branchSame,
                   business_branch=Val(hit,"CodigoSucursal"),
                   itil_branch=byRank[rank].Branch,
                   explicit_request_label=true,
                   same_company_provider_route=true,history_not_read=true
                });
              }
            }
         }
      }
   }
   int typedNone=0,typedOne=0,typedMultiple=0,typedNoLabel=0,typedWrongOnly=0,typedSupported=0;
   foreach(int rank in Enumerable.Range(1,100)){
     var set=typedVerified[rank];
     if(sourceCompanies[rank]=="1"||sourceCompanies[rank]=="3")typedSupported++;
     if(set.Count==1)typedOne++;
     else if(set.Count>1)typedMultiple++;
     else{
       typedNone++;
       if(!typedSources.Keys.Any(x=>x.Rank==rank))typedNoLabel++;
       else if(typedWrongRanks.Contains(rank))typedWrongOnly++;
     }
   }
   Need(typedNone+typedOne+typedMultiple==100,"QA_TYPED_CASES_NOT_100");
   var decisions=Enumerable.Range(1,100).Select(rank=>{
     int linked=typedVerified[rank].Count;
     bool candidate=typedSources.Keys.Any(x=>x.Rank==rank);
     bool companyOk=sourceCompanies[rank]=="1"||sourceCompanies[rank]=="3";
     string status=!companyOk?"COMPANY_PROVIDER_ROUTE_NOT_CERTIFIED"
       :!candidate?"NO_EXPLICIT_TYPED_BUSINESS_KEY_IN_REQUEST"
       :linked==0 && typedWrongRanks.Contains(rank)?"FOREIGN_BRANCH_MATCH_REJECTED"
       :linked==0?"EXPLICIT_TYPED_KEY_NOT_FOUND_IN_COMPANY_DB"
       :linked==1?"SINGLE_EXACT_TYPED_PK_QA_OBSERVATION"
       :"MULTIPLE_EXACT_TYPED_PKS_NO_PRIMARY_INFERRED";
     return new{rank,case_sha256=byRank[rank].CaseSha,status,
       typed_business_link_count=linked,
       company_route_verified=companyOk,
       timestamp_only_november_qa=true,
       historical_causality_certified=false,
       repair_certified=false};
   }).ToArray();
   Need(decisions.Length==100,"QA_TYPED_DECISION_COUNT");
   int none=0,withoutCandidates=0,noMatch=0,one=0,many=0,mixed=0,wrongOnly=0;
   var ranksWithAny=matches.Select(x=>JsonSerializer.SerializeToElement(x).GetProperty("rank").GetInt32()).ToHashSet();
   for(int rank=1;rank<=100;rank++){
     int kinds=caseKinds[rank].Count;
     if(kinds==0){
        none++;
        if(!byCandidate.Values.Any(a=>a.Contains(rank)))withoutCandidates++;
        else if(ranksWithAny.Contains(rank))wrongOnly++;
        else noMatch++;
     } else if(kinds==1)one++;
     else many++;
     if(caseKinds[rank].Select(k=>k.Kind).Distinct().Count()>1)mixed++;
   }
   Need(none+one+many==100,"QA_AUG100_CASE_ACCOUNTING_DRIFT");
   var report=new {
      schema=Schema,qa_server="ELSE70",period="2026-08",
      selection="FIRST_100_FechaSolicitud_CodigoIncidente_ASC",
      first_opened_at=frozen[0].GetProperty("opened_at").GetString(),
      last_opened_at=frozen[99].GetProperty("opened_at").GetString(),
      frozen_source_sha256=Hash(srcRaw),
      source_cases=1819,evaluated_cases=100,
      candidate_19digit_mentions=candidateTotal,
      distinct_candidate_numbers=candidatesAll.Length,
      sql_pk_select_batches=reads,examined_database_count=13,
      total_db_pk_observations=matches.Count,
      same_branch_observations=sameBranchObservations,
      wrong_branch_observations=wrongBranchObservations,
      cases_no_valid_pk=none,cases_no_19digit_candidate=withoutCandidates,
      cases_19digit_no_pk_anywhere_queried=noMatch,
      cases_wrong_branch_only=wrongOnly,
      cases_one_valid_pk=one,cases_multiple_valid_pk=many,
      cases_with_both_kinds=mixed,
      typed_company_route_supported_cases=typedSupported,
      typed_cases_with_source_label=typedSources.Keys.Select(x=>x.Rank).Distinct().Count(),
      typed_labeled_values=typedSources.Values.Sum(x=>x.Count),
      typed_company_provider_select_batches=typedSelects,
      typed_pk_observations=typedMatches.Count,
      typed_company_branch_match_observations=typedSame,
      typed_wrong_branch_observations=typedWrong,
      typed_cases_with_one_pk=typedOne,typed_cases_with_multiple_pks=typedMultiple,
      typed_cases_with_any_pk=typedOne+typedMultiple,
      typed_cases_without_any_pk=typedNone,
      typed_cases_without_source_label=typedNoLabel,
      typed_cases_wrong_branch_only=typedWrongOnly,
      typed_missing_table_schema_types=typedMissingKinds.OrderBy(x=>x).ToArray(),
      typed_labels_used_no_history=true,
      legacy_generic_cross_db_matches_are_not_promoted_to_authority=true,
      exact_company_provider_and_explicit_label_mandatory_for_typed_claim=true,
      per_case_statuses=decisions.GroupBy(x=>x.status).ToDictionary(g=>g.Key,g=>g.Count()),
      typed_source_expanded_beyond_original_1800=true,
      observed_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture),
      solution_read=false,causes_certified=0,repairs_certified=0,
      august_historical_business_state_verified=false,business_writes=0
   };
   string sourceSha=Hash(File.ReadAllBytes(Path.Combine(Root,Reader)));
   byte[] payload=JsonSerializer.SerializeToUtf8Bytes(new {
      schema=Schema,source_sha256=sourceSha,report,case_metadata=cases,matches,typed_matches=typedMatches,
      case_decisions=decisions,
      read_only=true,history_not_read=true,business_writes=0
   });
   string digest=Hash(payload);
   string path=Path.Combine(Root,"aug_first100_company_typed.private.json");
   using(var fs=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.None))
      fs.Write(payload);
   string mac=Convert.ToHexString(HMACSHA256.HashData(key,Encoding.UTF8.GetBytes(
      Schema+":"+sourceSha+":"+digest))).ToLowerInvariant();
   using(var fs=new FileStream(path+".proof.json",FileMode.CreateNew,FileAccess.Write,FileShare.None))
     fs.Write(JsonSerializer.SerializeToUtf8Bytes(new{
      schema=Schema+"-hmac.v1",source_sha256=sourceSha,receipt_sha256=digest,
      hmac_sha256=mac,read_only=true
   }));
   Console.WriteLine(JsonSerializer.Serialize(new {status="AUG_FIRST100_COMPANY_TYPED_QA_SUCCESS",report,receipt_sha256=digest}));
 }
}
