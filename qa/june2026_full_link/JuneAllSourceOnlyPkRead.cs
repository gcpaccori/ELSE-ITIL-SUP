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

// Entire 1,621 original June ITIL request cohort. The pre-existing source
// HMAC proves exact source identity and ordering. Historical solutions are
// NOT queried, labels are NOT imported, and BOTH PK types are queried.
// All connections point exclusively to ELSE70 QA. All business queries are
// parameterized SELECT with fixed allowlisted DB/table and PK column names.
internal static class JuneAllSourceOnlyPkRead {
 const string Root=@"C:\Temp\ELSE_ITIL_JUNEALL_LINK_20261113";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string SourceSchema="else.itil.qa.2026-juneall-source.v1";
 const string SourceProof="else.itil.qa.2026-juneall-source-hmac.v1";
 const string Schema="else.itil.qa.2026-june1621-source-only-dual-pk-discovery.v1";
 const string Proof="else.itil.qa.2026-june1621-source-only-dual-pk-discovery-hmac.v1";
 const string Reader="JuneAllSourceOnlyPkRead.cs";
 static readonly string[] Databases={
  "dbComercial001_D","dbComercial003_D","dbComercial004_D",
  "dbComercial006_D","dbComercial007_D","dbComercial008_D",
  "dbComercial100_D","dbComercial200_D",
  "dbComercial001_Diario","dbComercial001_20230131",
  "dbComercial003_mayo","dbGerencial_D","dbDistribucion_D"
 };
 static string Hash(byte[] s)=>Convert.ToHexString(SHA256.HashData(s)).ToLowerInvariant();
 static string Hash(string s)=>Hash(Encoding.UTF8.GetBytes(s));
 static string Hmac(byte[] key,string s)=>Convert.ToHexString(
  HMACSHA256.HashData(key,Encoding.UTF8.GetBytes(s))).ToLowerInvariant();
 static string Val(DataRow r,string k)=>r.IsNull(k)?"":Convert.ToString(r[k],CultureInfo.InvariantCulture)??"";
 static void Need(bool b,string err){if(!b)throw new Exception(err);}
 static DataTable Exec(AccesoDatos db,string stmt,string signature="",params SqlParameter[] parameters){
   var args=new List<SqlParameter>{
     new("@stmt",SqlDbType.NVarChar,-1){Value=stmt},
     new("@params",SqlDbType.NVarChar,-1){Value=signature}
   };
   args.AddRange(parameters);
   var result=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args.ToArray());
   Need(result!=null&&result.Tables.Count>0,"FULL_JUNE_SQL_NOT_RETURNED");
   return result!.Tables[0];
 }
 static void Main(){
   Directory.CreateDirectory(Root);
   foreach(var name in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
     if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(name))){
       var value=Environment.GetEnvironmentVariable(name,EnvironmentVariableTarget.Machine);
       Need(!string.IsNullOrWhiteSpace(value),"FULL_JUNE_CORPORATE_ENV_MISSING");
       Environment.SetEnvironmentVariable(name,value);
     }
   }
   byte[] key=File.ReadAllBytes(Signer);
   Need(key.Length==32,"FULL_JUNE_SIGNER_INVALID");
   byte[] sourceRaw=File.ReadAllBytes(Path.Combine(Root,"juneall_202606.private.json"));
   using var srcJson=JsonDocument.Parse(sourceRaw);
   using var sourceProof=JsonDocument.Parse(File.ReadAllBytes(
      Path.Combine(Root,"juneall_202606.private.json.proof.json")));
   var src=srcJson.RootElement;
   var sp=sourceProof.RootElement;
   string sourceFileHash=Hash(sourceRaw),authorCodeHash=src.GetProperty("source_sha256").GetString()??"";
   Need(src.GetProperty("schema").GetString()==SourceSchema
     &&src.GetProperty("period").GetString()=="2026-06"
     &&src.GetProperty("source").GetString()=="dbITIL_D/dbo.taIncidente"
     &&src.GetProperty("history_or_resolution_read").GetBoolean()==false
     &&src.GetProperty("read_only").GetBoolean()
     &&src.GetProperty("business_modifications").GetInt32()==0
     &&src.GetProperty("selected").GetInt32()==1621
     &&sp.GetProperty("schema").GetString()==SourceProof
     &&sp.GetProperty("source_sha256").GetString()==authorCodeHash
     &&sp.GetProperty("receipt_sha256").GetString()==sourceFileHash
     &&sp.GetProperty("hmac_sha256").GetString()==Hmac(
        key,SourceSchema+":"+authorCodeHash+":"+sourceFileHash),
     "FULL_JUNE_SOURCE_HMAC_NOT_AUTHENTIC");
   var frozen=src.GetProperty("results").EnumerateArray().ToArray();
   Need(frozen.Length==1621,"FULL_JUNE_SOURCE_NOT_1621");

   var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string root=xml.Descendants("connectionStrings").Descendants("add")
      .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
      .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
      ??throw new Exception("FULL_JUNE_QA_ROOT_NOT_FOUND");
   Need(root.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)
      &&root.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),
      "FULL_JUNE_ROOT_NOT_QA");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(root));
   var itil=provider.Obtener(eSistema.ITIL,(byte)1);
   var commercial=provider.Obtener(eSistema.Comercial,(byte)1);
   Need(itil.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
      &&itil.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase)
      &&commercial.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
      &&commercial.cdnConexion.NombreBaseDatos.Equals("dbComercial001_D",StringComparison.OrdinalIgnoreCase),
      "FULL_JUNE_WRONG_QA_DB");

   var itilRows=Exec(itil,@"SELECT CodigoIncidente,FechaSolicitud,CodigoEmpresa,
      CodigoSucursal,CodigoModulo,CodigoServicio,DescripcionSolicitud
      FROM dbo.taIncidente
      WHERE FechaSolicitud>=@start AND FechaSolicitud<@end
      ORDER BY FechaSolicitud DESC,CodigoIncidente DESC",
      "@start datetime,@end datetime",
      new SqlParameter("@start",SqlDbType.DateTime){Value=new DateTime(2026,6,1)},
      new SqlParameter("@end",SqlDbType.DateTime){Value=new DateTime(2026,7,1)});
   Need(itilRows.Rows.Count==1621,"FULL_JUNE_LIVE_QA_COUNT_CHANGED");

   var caseEntries=new List<object>();
   var requestNums=new Dictionary<long,List<int>>();
   var byRank=new Dictionary<int,(string CaseSha,string Branch,string Module)>();
   int validValues=0,overflow=0;
   for(int i=0;i<1621;i++){
      int rank=i+1;
      DataRow row=itilRows.Rows[i];
      var expected=frozen[i];
      string caseSha=Hash(Val(row,"CodigoIncidente"));
      string req=Val(row,"DescripcionSolicitud");
      string module=Val(row,"CodigoModulo").TrimEnd();
      string service=Val(row,"CodigoServicio").TrimEnd();
      DateTime opened=(DateTime)row["FechaSolicitud"];
      string openedAt=opened.ToString("yyyy-MM-ddTHH:mm:ss",CultureInfo.InvariantCulture);
      Need(expected.GetProperty("rank").GetInt32()==rank
        &&expected.GetProperty("case_sha256").GetString()==caseSha
        &&expected.GetProperty("description_sha256").GetString()==Hash(req)
        &&expected.GetProperty("company").GetString()==Val(row,"CodigoEmpresa")
        &&expected.GetProperty("module_code").GetString()==module
        &&expected.GetProperty("service_code").GetString()==service
        &&expected.GetProperty("opened_at").GetString()==openedAt
        &&expected.GetProperty("historical_solution_not_read").GetBoolean(),
        "FULL_JUNE_ORIGINAL_CASE_REQUEST_NOT_BOUND");
      var nums=new HashSet<long>();
      foreach(Match match in Regex.Matches(req,@"(?<!\d)\d{19}(?!\d)",RegexOptions.CultureInvariant)){
         if(long.TryParse(match.Value,NumberStyles.None,CultureInfo.InvariantCulture,out long n)){
            if(nums.Add(n))validValues++;
         }else overflow++;
      }
      Need(nums.Count<=150,"FULL_JUNE_CASE_TOO_MANY_NUMERIC_CANDIDATES");
      foreach(long n in nums){
         if(!requestNums.ContainsKey(n))requestNums[n]=new();
         requestNums[n].Add(rank);
      }
      byRank[rank]=(caseSha,Val(row,"CodigoSucursal"),module);
      caseEntries.Add(new{
         rank,case_sha256=caseSha,
         request_sha256=Hash(req),
         module_code=module,service_code=service,
         itil_company=Val(row,"CodigoEmpresa"),
         itil_branch=Val(row,"CodigoSucursal"),
         opened_at=openedAt,
         request_numeric_candidates=nums.Count,
         numeric_candidates_sha256=nums.Select(n=>Hash(n.ToString(CultureInfo.InvariantCulture)))
           .OrderBy(x=>x).ToArray(),
         source_original_request_only=true,known_history_not_read=true
      });
   }
   var dbTable=Exec(commercial,@"SELECT name FROM sys.databases WHERE state_desc='ONLINE'
     AND name IN('dbComercial001_D','dbComercial003_D','dbComercial004_D',
     'dbComercial006_D','dbComercial007_D','dbComercial008_D',
     'dbComercial100_D','dbComercial200_D','dbComercial001_Diario',
     'dbComercial001_20230131','dbComercial003_mayo',
     'dbGerencial_D','dbDistribucion_D')");
   var online=new HashSet<string>(dbTable.Rows.Cast<DataRow>().Select(x=>Val(x,"name")));
   Need(online.Count==13,"FULL_JUNE_NOT_ALL_DB_VISIBLE");
   var allNumbers=requestNums.Keys.OrderBy(x=>x).ToArray();
   var matches=new List<object>();
   var presence=new List<object>();
   var errors=new List<string>();
   int queryCount=0;
   foreach(string database in Databases){
      var metadata=Exec(commercial,$@"SELECT t.name AS table_name,
        MAX(CASE WHEN c.name='CodigoSucursal' THEN 1 ELSE 0 END) AS has_branch
        FROM [{database}].sys.tables t
        JOIN [{database}].sys.schemas s ON s.schema_id=t.schema_id
        JOIN [{database}].sys.columns c ON c.object_id=t.object_id
        WHERE s.name='dbo' AND t.name IN('taOrdenTrabajo','taCobranza')
        GROUP BY t.name");
      var tbl=metadata.Rows.Cast<DataRow>()
        .ToDictionary(r=>Val(r,"table_name"),r=>Val(r,"has_branch")=="1");
      foreach(string kind in new[]{"OT","COLLECTION"}){
         string table=kind=="OT"?"taOrdenTrabajo":"taCobranza";
         string pk=kind=="OT"?"CodigoOrdenTrabajo":"CodigoCobranza";
         if(!tbl.TryGetValue(table,out bool hasBranch)){
            presence.Add(new{database,kind,table_present=false,
              branch_column_present=false,lookup_batches=0});continue;
         }
         Need(hasBranch,"FULL_JUNE_BUSINESS_BRANCH_COLUMN_ABSENT");
         int batches=0;
         for(int j=0;j<allNumbers.Length;j+=160){
            var nums=allNumbers.Skip(j).Take(160).ToArray();
            var parameters=nums.Select((n,k)=>new SqlParameter("@n"+k,SqlDbType.BigInt){Value=n}).ToArray();
            string sql=$@"SELECT {pk},CodigoSucursal FROM [{database}].dbo.{table}
                    WHERE {pk} IN ({string.Join(",",parameters.Select(x=>x.ParameterName))})";
            var data=Exec(commercial,sql,string.Join(",",
                parameters.Select(x=>x.ParameterName+" bigint")),parameters);
            Need(data.Rows.Count<=nums.Length,"FULL_JUNE_PK_NOT_ONE_ROW_PER_VALUE");
            foreach(DataRow hit in data.Rows){
                long n=Convert.ToInt64(hit[pk],CultureInfo.InvariantCulture);
                Need(requestNums.TryGetValue(n,out var originRanks),
                     "FULL_JUNE_RETURNED_PK_NOT_IN_ORIGINAL_SOURCE");
                foreach(int rank in originRanks!){
                    var caseScope=byRank[rank];
                    bool branchSame=Val(hit,"CodigoSucursal")==caseScope.Branch;
                    matches.Add(new{
                       rank,case_sha256=caseScope.CaseSha,
                       module_code=caseScope.Module,
                       kind,source_database=database,primary_key_column=pk,
                       primary_key_private=n.ToString(CultureInfo.InvariantCulture),
                       primary_key_sha256=Hash(n.ToString(CultureInfo.InvariantCulture)),
                       business_branch=Val(hit,"CodigoSucursal"),
                       itil_branch=caseScope.Branch,
                       business_branch_matches_itil=branchSame,
                       current_qa_row_found=true,history_not_read=true,
                       native_ticket_business_fk_certified=false
                    });
                }
            }
            queryCount++;batches++;
         }
         presence.Add(new{database,kind,table_present=true,
           branch_column_present=hasBranch,lookup_batches=batches});
      }
   }
   string codeSha=Hash(File.ReadAllBytes(Path.Combine(Root,Reader)));
   var output=new{
     schema=Schema,source_sha256=codeSha,
     original_june1621_receipt_sha256=sourceFileHash,
     qa_itil="ELSE70/dbITIL_D",qa_search_databases=13,
     source_cases=1621,input_request_only=true,
     known_history_not_read=true,no_module_gold_labels_used=true,
     original_request_numeric_regex=@"(?<!\d)\d{19}(?!\d)",
     valid_case_candidate_count=validValues,
     overflow_19_digit_candidates=overflow,
     distinct_candidate_numbers=allNumbers.Length,
     business_sql_select_batches=queryCount,
     case_metadata=caseEntries,business_key_matches=matches,
     table_lookup_coverage=presence,
     lookup_errors=errors,
     observed_at_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture),
     actual_june_as_of_business_state_not_proven=true,
     no_writer_sql_executed=true,read_only=true,business_writes=0
   };
   byte[] raw=JsonSerializer.SerializeToUtf8Bytes(output);
   string receiptSha=Hash(raw);
   var filename=Path.Combine(Root,"june1621_source_only_dualpk.private.json");
   File.WriteAllBytes(filename,raw);
   File.WriteAllBytes(filename+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
      schema=Proof,source_sha256=codeSha,receipt_sha256=receiptSha,
      hmac_sha256=Hmac(key,Schema+":"+codeSha+":"+receiptSha),
      read_only=true
   }));
   Console.WriteLine(JsonSerializer.Serialize(new{
      status="JUNE1621_SOURCE_ONLY_DUAL_PK_READ_COMPLETE",
      source_cases=1621,candidate_numbers=validValues,distinct_numbers=allNumbers.Length,
      query_count=queryCount,matched_case_db_pk_rows=matches.Count,
      distinct_cases_with_match=matches.Select(x=>JsonSerializer.SerializeToElement(x)
       .GetProperty("rank").GetInt32()).Distinct().Count(),
      receipt_sha256=receiptSha,business_writes=0
   }));
 }
}
