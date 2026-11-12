using System;
using System.Data;
using System.Data.SqlClient;
using System.Collections.Generic;
using System.Linq;
using System.Globalization;
using System.Text.Json;
using System.Text;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.IO;
using System.Xml.Linq;
using SIELSEAccesoDatos;

// Follow-up on two still-unmatched June requests (120,800), READ ONLY.
// Search candidate numeric values from *original request* as alternative
// business keys (supply, collection, OT), not merely taOrdenTrabajo PK.
// Results do not establish one-to-one ticket/object relationships.
internal static class June57ResidualRelationRead {
 const string Root=@"C:\Temp\ELSE_ITIL_JUNE57_IDENTIFIER_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.2026-june57-two-residual-request-key-probe.v1";
 const string Proof="else.itil.qa.2026-june57-two-residual-request-key-probe-hmac.v1";
 const string MS="else.itil.qa.2026-june57-source-and-history-reference-selection.v1";
 const string MP="else.itil.qa.2026-june57-source-and-history-reference-hmac.v1";
 static readonly int[] Ranks={120,800};
 static readonly string[] DB={
 "dbComercial001_D","dbComercial003_D","dbComercial004_D","dbComercial006_D",
 "dbComercial007_D","dbComercial008_D","dbComercial100_D","dbComercial200_D",
 "dbComercial001_Diario","dbComercial001_20230131","dbComercial003_mayo",
 "dbGerencial_D","dbDistribucion_D"
 };
 static readonly string[] Relations={
 "taOrdenTrabajo.CodigoOrdenTrabajo",
 "taOrdenTrabajo.CodigoSuministro",
 "taSuministro.CodigoSuministro",
 "taCobranza.CodigoCobranza",
 "taCobranza.CodigoSuministro"
 };
 static void Need(bool b,string e){if(!b)throw new Exception(e);}
 static string Sha(byte[] raw)=>Convert.ToHexString(SHA256.HashData(raw)).ToLowerInvariant();
 static string Sha(string s)=>Sha(Encoding.UTF8.GetBytes(s));
 static string Mac(byte[] key,string msg)=>Convert.ToHexString(HMACSHA256.HashData(key,Encoding.UTF8.GetBytes(msg))).ToLowerInvariant();
 static string Val(DataRow r,string c)=>r.IsNull(c)?"":Convert.ToString(r[c],CultureInfo.InvariantCulture)??"";
 static DataTable Q(AccesoDatos db,string stmt, string param="",params SqlParameter[] inputs){
    var args=new List<SqlParameter>{
      new("@stmt",SqlDbType.NVarChar,-1){Value=stmt},
      new("@params",SqlDbType.NVarChar,-1){Value=param}
    };
    args.AddRange(inputs);
    var data=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args.ToArray());
    Need(data!=null&&data.Tables.Count>0,"RESIDUAL_SQL_MISSING_RESULT");
    return data!.Tables[0];
 }
 static void Main(){
   Directory.CreateDirectory(Root);
   foreach(var k in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
      if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(k))){
        var v=Environment.GetEnvironmentVariable(k,EnvironmentVariableTarget.Machine);
        Need(!string.IsNullOrWhiteSpace(v),"RESIDUAL_ENV_MISSING");
        Environment.SetEnvironmentVariable(k,v);
      }
   }
   byte[] key=File.ReadAllBytes(Signer);
   Need(key.Length==32,"RESIDUAL_SIGNER_BAD");
   byte[] mbytes=File.ReadAllBytes(Path.Combine(Root,"june57_manifest.private.json"));
   using var mj=JsonDocument.Parse(mbytes);
   using var pj=JsonDocument.Parse(File.ReadAllBytes(Path.Combine(Root,"june57_manifest.private.json.proof.json")));
   var signed=mj.RootElement;
   string hash=Sha(mbytes),source=signed.GetProperty("source_sha256").GetString()??"";
   Need(signed.GetProperty("schema").GetString()==MS
     &&pj.RootElement.GetProperty("schema").GetString()==MP
     &&pj.RootElement.GetProperty("receipt_sha256").GetString()==hash
     &&pj.RootElement.GetProperty("hmac_sha256").GetString()==Mac(key,MS+":"+source+":"+hash),
     "RESIDUAL_UNSIGNED_SELECTION");
   var selected=signed.GetProperty("rows").EnumerateArray().ToArray();
   Need(selected.Length==57 && Ranks.All(x=>selected.Any(r=>r.GetProperty("rank").GetInt32()==x)),
     "RESIDUAL_INVALID_SOURCE_SCOPE");
   var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   var config=xml.Descendants("connectionStrings").Descendants("add")
      .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
      .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
      ??throw new Exception("RESIDUAL_ROOT_MISSING");
   Need(config.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)
     &&config.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"RESIDUAL_NOT_QA");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(config));
   var itil=provider.Obtener(eSistema.ITIL,(byte)1);
   var business=provider.Obtener(eSistema.Comercial,(byte)1);
   Need(itil.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
      &&itil.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase)
      &&business.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
      &&business.cdnConexion.NombreBaseDatos.Equals("dbComercial001_D",StringComparison.OrdinalIgnoreCase),
      "RESIDUAL_QA_ROUTE_DRIFT");
   const string sql=@"WITH X AS(
    SELECT ROW_NUMBER() OVER(ORDER BY FechaSolicitud DESC,CodigoIncidente DESC) AS rank,
    CodigoIncidente,CodigoSucursal,DescripcionSolicitud
    FROM dbo.taIncidente WHERE FechaSolicitud>=@start AND FechaSolicitud<@end)
    SELECT * FROM X WHERE rank IN(120,800) ORDER BY rank";
   var it=Q(itil,sql,"@start datetime,@end datetime",
      new("@start",SqlDbType.DateTime){Value=new DateTime(2026,6,1)},
      new("@end",SqlDbType.DateTime){Value=new DateTime(2026,7,1)});
   Need(it.Rows.Count==2,"RESIDUAL_NOT_EXACT_TWO");
   var observations=new List<object>();
   var inputs=new List<(int Rank,string Branch,long Value,string Sha)>();
   foreach(DataRow row in it.Rows) {
      int rank=Convert.ToInt32(row["rank"],CultureInfo.InvariantCulture);
      var m=selected.Single(x=>x.GetProperty("rank").GetInt32()==rank);
      string req=Val(row,"DescripcionSolicitud"),caseSha=Sha(Val(row,"CodigoIncidente"));
      Need(m.GetProperty("case_sha256").GetString()==caseSha
         &&m.GetProperty("request_sha256").GetString()==Sha(req),
         "RESIDUAL_CASE_NOT_BOUND_TO_ORIGINAL");
      var nums=new HashSet<long>();
      foreach(Match match in Regex.Matches(req,@"(?<!\d)\d{9,19}(?!\d)",RegexOptions.CultureInvariant)){
         if(long.TryParse(match.Value,NumberStyles.None,CultureInfo.InvariantCulture,out long x))nums.Add(x);
      }
      Need(nums.Count<=20,"RESIDUAL_TOO_MANY_NUMERIC_REFERENCES");
      foreach(long n in nums)inputs.Add((rank,Val(row,"CodigoSucursal"),n,Sha(n.ToString(CultureInfo.InvariantCulture))));
      observations.Add(new{
         rank,case_sha256=caseSha,
         original_request_sha256=Sha(req),
         candidate_numeric_count=nums.Count,
         candidate_sha256=nums.Select(x=>Sha(x.ToString(CultureInfo.InvariantCulture))).OrderBy(x=>x).ToArray(),
         no_historical_solution_read=true
      });
   }
   var available=Q(business,@"SELECT name FROM sys.databases WHERE state_desc='ONLINE'
      AND name IN ('dbComercial001_D','dbComercial003_D','dbComercial004_D',
      'dbComercial006_D','dbComercial007_D','dbComercial008_D',
      'dbComercial100_D','dbComercial200_D','dbComercial001_Diario',
      'dbComercial001_20230131','dbComercial003_mayo','dbGerencial_D',
      'dbDistribucion_D')");
   var online=new HashSet<string>(available.Rows.Cast<DataRow>().Select(x=>Val(x,"name")));
   var lookup=new List<object>();
   int queryCount=0;
   foreach(string db in DB){
      if(!online.Contains(db))continue;
      var cols=Q(business,$@"SELECT t.name AS tab, c.name AS col FROM [{db}].sys.tables t
        JOIN [{db}].sys.schemas s ON s.schema_id=t.schema_id
        JOIN [{db}].sys.columns c ON c.object_id=t.object_id
        WHERE s.name='dbo' AND t.name IN ('taOrdenTrabajo','taSuministro','taCobranza')
          AND c.name IN ('CodigoOrdenTrabajo','CodigoSuministro','CodigoCobranza','CodigoSucursal')");
      var names=new HashSet<string>(cols.Rows.Cast<DataRow>().Select(x=>Val(x,"tab")+"."+Val(x,"col")));
      foreach(string rel in Relations){
         if(!names.Contains(rel))continue;
         var parts=rel.Split('.');
         string table=parts[0],column=parts[1];
         bool branchAvailable=names.Contains(table+".CodigoSucursal");
         foreach(var candidate in inputs){
            string stmt=branchAvailable?
              $@"SELECT COUNT_BIG(*) AS n,COALESCE(SUM(CASE WHEN CONVERT(varchar(20),CodigoSucursal)=@branch THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END),0) AS same_branch
              FROM [{db}].dbo.{table} WHERE {column}=@id":
              $@"SELECT COUNT_BIG(*) AS n,CONVERT(bigint,0) AS same_branch
              FROM [{db}].dbo.{table} WHERE {column}=@id";
            var ps=branchAvailable?new[]{
              new SqlParameter("@id",SqlDbType.BigInt){Value=candidate.Value},
              new SqlParameter("@branch",SqlDbType.VarChar,20){Value=candidate.Branch}
            }:new[]{new SqlParameter("@id",SqlDbType.BigInt){Value=candidate.Value}};
            var found=Q(business,stmt,
              branchAvailable?"@id bigint,@branch varchar(20)":"@id bigint",ps);
            queryCount++;
            Need(found.Rows.Count==1,"RESIDUAL_COUNT_QUERY_NOT_ONE_RESULT");
            long n=Convert.ToInt64(found.Rows[0]["n"],CultureInfo.InvariantCulture);
            long same=Convert.ToInt64(found.Rows[0]["same_branch"],CultureInfo.InvariantCulture);
            Need(n>=0&&same>=0&&same<=n,"RESIDUAL_BAD_BUSINESS_COUNTS");
            if(n>0)lookup.Add(new{
              rank=candidate.Rank,source_candidate_sha256=candidate.Sha,
              identifier_private=candidate.Value.ToString(CultureInfo.InvariantCulture),
              database=db,table,column,records=n,same_itil_branch=same,
              unique_business_row=(n==1),request_identity_not_certified=true,
              historical_note_read=false
            });
         }
      }
   }
   string code=Sha(File.ReadAllBytes(Path.Combine(Root,"June57ResidualRelationRead.cs")));
   var output=new{
      schema=Schema,source_sha256=code,
      june57_selection_receipt_sha256=hash,
      qa_itil="ELSE70/dbITIL_D",
      source_cases=2,cases=observations,
      lookup_results=lookup,select_queries=queryCount,
      search_type="ALTERNATIVE_PK_OR_FOREIGN_KEY_9_TO_19_DIGIT",
      no_historical_note_read=true,
      read_only=true,no_writes=true,repairs_certified=0
   };
   byte[] raw=JsonSerializer.SerializeToUtf8Bytes(output);
   string receiptSha=Sha(raw);
   string dest=Path.Combine(Root,"june57_residual_source_relation.private.json");
   File.WriteAllBytes(dest,raw);
   File.WriteAllBytes(dest+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
       schema=Proof,source_sha256=code,receipt_sha256=receiptSha,
       hmac_sha256=Mac(key,Schema+":"+code+":"+receiptSha),read_only=true
   }));
   Console.WriteLine(JsonSerializer.Serialize(new{
      status="TWO_RESIDUAL_SOURCE_RELATION_SCAN_PASS",
      input_cases=2,input_candidates=inputs.Count,
      query_count=queryCount,matches=lookup.Count,
      matched_cases=lookup.Select(x=>JsonSerializer.SerializeToElement(x).GetProperty("rank").GetInt32()).Distinct().Count(),
      receipt_sha256=receiptSha,business_writes=0
   }));
 }
}
