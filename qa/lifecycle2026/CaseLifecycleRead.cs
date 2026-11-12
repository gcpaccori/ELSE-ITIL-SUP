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
using System.Xml.Linq;
using SIELSEAccesoDatos;

// Fixed read-only 2026 ITIL lifecycle query over native CodigoIncidente keys.
// This establishes equality of observed keys, NOT a declared foreign key.
// HMAC source cohorts and fresh exact top-100 order are checked first.
// No users, comments, SQL fragments from tickets or original IDs are exported.
internal static class CaseLifecycleRead {
 const string Root=@"C:\Temp\ELSE_ITIL_WORKFLOW_QA_20261112";
 const string Monthly=@"C:\Temp\ELSE_ITIL_MONTHEND2026_QA_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.2026-case-lifecycle-native-keys.v1";
 const string ProofSchema="else.itil.qa.2026-case-lifecycle-hmac.v1";
 const string MonthSchema="else.itil.qa.2026-monthend100-source.v1";
 static string Hex(byte[] input)=>Convert.ToHexString(SHA256.HashData(input)).ToLowerInvariant();
 static string Sha(string text)=>Hex(Encoding.UTF8.GetBytes(text));
 static void Need(bool value,string code){if(!value)throw new Exception(code);}
 static string Val(DataRow r,string k)=>r.IsNull(k)?"":Convert.ToString(r[k],CultureInfo.InvariantCulture)??"";
 static long N(DataRow r,string k)=>Convert.ToInt64(r[k],CultureInfo.InvariantCulture);
 static string Mac(string schema,string source,string receipt,byte[] key)=>
   Convert.ToHexString(HMACSHA256.HashData(key,
       Encoding.UTF8.GetBytes(schema+":"+source+":"+receipt))).ToLowerInvariant();
 static DataTable Q(AccesoDatos db,string query,string argspec="",SqlParameter[]? parameters=null){
    var args=new List<SqlParameter>{
      new("@stmt",SqlDbType.NVarChar,-1){Value=query},
      new("@params",SqlDbType.NVarChar,150){Value=argspec}
    };
    if(parameters!=null)args.AddRange(parameters);
    var d=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args.ToArray());
    Need(d!=null&&d.Tables.Count>0,"QA_RESULT_TABLE_UNAVAILABLE");
    return d!.Tables[0];
 }
 static SqlParameter[] Window(DateTime a,DateTime b)=>new[]{
    new SqlParameter("@start",SqlDbType.DateTime){Value=a},
    new SqlParameter("@end",SqlDbType.DateTime){Value=b}
 };
 static (JsonDocument,string) SignedSource(string ym,string codeSha,byte[] key){
   string path=Path.Combine(Monthly,"monthend_"+ym+".private.json");
   byte[] raw=File.ReadAllBytes(path);
   var doc=JsonDocument.Parse(raw);
   var proof=JsonDocument.Parse(File.ReadAllBytes(path+".proof.json"));
   var d=doc.RootElement;var p=proof.RootElement;
   string hash=Hex(raw);
   Need(d.GetProperty("schema").GetString()==MonthSchema &&
        d.GetProperty("period").GetString()==ym[..4]+"-"+ym[4..] &&
        d.GetProperty("selected").GetInt32()==100 &&
        d.GetProperty("source_sha256").GetString()==codeSha &&
        p.GetProperty("source_sha256").GetString()==codeSha &&
        p.GetProperty("receipt_sha256").GetString()==hash &&
        p.GetProperty("read_only").GetBoolean() &&
        !d.GetProperty("history_or_resolution_read").GetBoolean() &&
        d.GetProperty("read_only").GetBoolean() &&
        Mac(MonthSchema,codeSha,hash,key)==p.GetProperty("hmac_sha256").GetString(),
        "MONTHLY_QA_RECEIPT_HMAC_OR_SCOPE_INVALID");
   Need(d.GetProperty("results").GetArrayLength()==100,"MONTHLY_SOURCE_RESULTS_INVALID");
   return (doc,hash);
 }
 const string PrimaryKeySql=@"SELECT t.name AS TableName,k.name AS ConstraintName,
    c.name AS ColumnName,ic.key_ordinal AS Ordinal
    FROM sys.key_constraints k
    JOIN sys.tables t ON t.object_id=k.parent_object_id
    JOIN sys.index_columns ic ON ic.object_id=t.object_id AND ic.index_id=k.unique_index_id
    JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
    WHERE k.type='PK' AND t.schema_id=SCHEMA_ID('dbo')
      AND t.name IN ('taIncidente','taIncidenteAtencion','taIncidenteDerivacion',
                     'taIncidenteEncuesta','taModulo','gnEstadoIncidente')
      AND ic.key_ordinal>0
    ORDER BY t.name,ic.key_ordinal";
 const string FkSql=@"SELECT fk.name AS ConstraintName,
    OBJECT_NAME(fk.parent_object_id) AS ParentTable,
    OBJECT_NAME(fk.referenced_object_id) AS TargetTable,
    fk.is_disabled AS Disabled,fk.is_not_trusted AS Untrusted
    FROM sys.foreign_keys fk
    WHERE fk.parent_object_id IN (
      OBJECT_ID('dbo.taIncidenteAtencion'),
      OBJECT_ID('dbo.taIncidenteDerivacion'),
      OBJECT_ID('dbo.taIncidenteEncuesta'),
      OBJECT_ID('dbo.taIncidente'))";
 const string FlowSql=@"WITH C AS (
    SELECT TOP (100) CodigoIncidente,FechaSolicitud,CodigoEmpresa,
           CodigoModulo,CodigoEstadoIncidente
    FROM dbo.taIncidente
    WHERE FechaSolicitud>=@start AND FechaSolicitud<@end
    ORDER BY FechaSolicitud DESC,CodigoIncidente DESC
   )
   SELECT C.CodigoIncidente,C.FechaSolicitud,C.CodigoEmpresa,
     C.CodigoModulo,C.CodigoEstadoIncidente,
     CAST(CASE WHEN m.CodigoModulo IS NULL THEN 0 ELSE 1 END AS int) AS ModuleKeyMatched,
     CAST(CASE WHEN es.CodigoEstadoIncidente IS NULL THEN 0 ELSE 1 END AS int) AS StateKeyMatched,
     es.Atendido AS StateDictionaryAtendido,
     (SELECT COUNT_BIG(1) FROM dbo.taIncidenteAtencion a
       WHERE a.CodigoIncidente=C.CodigoIncidente) AS AttentionRows,
     (SELECT COUNT_BIG(1) FROM dbo.taIncidenteAtencion a
       WHERE a.CodigoIncidente=C.CodigoIncidente AND a.Solucionado=1) AS AttentionMarkedSolved,
     (SELECT COUNT_BIG(1) FROM dbo.taIncidenteAtencion a
       WHERE a.CodigoIncidente=C.CodigoIncidente
       AND a.FechaHoraFinAtencion IS NOT NULL) AS AttentionHasFinish,
     (SELECT COUNT_BIG(1) FROM dbo.taIncidenteDerivacion d
       WHERE d.CodigoIncidente=C.CodigoIncidente) AS DerivationRows,
     (SELECT COUNT_BIG(1) FROM dbo.taIncidenteEncuesta e
       WHERE e.CodigoIncidente=C.CodigoIncidente) AS SurveyRows
   FROM C
   LEFT JOIN dbo.taModulo m ON m.CodigoModulo=C.CodigoModulo
   LEFT JOIN dbo.gnEstadoIncidente es ON es.CodigoEstadoIncidente=C.CodigoEstadoIncidente
   ORDER BY C.FechaSolicitud DESC,C.CodigoIncidente DESC";
 static int Main(){
  try{
    Directory.CreateDirectory(Root);
    foreach(string k in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
       if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(k))){
          var v=Environment.GetEnvironmentVariable(k,EnvironmentVariableTarget.Machine);
          Need(!string.IsNullOrWhiteSpace(v),"QA_CONNECTOR_MISSING");
          Environment.SetEnvironmentVariable(k,v);
       }
    }
    var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
    string cs=xml.Descendants("connectionStrings").Descendants("add")
      .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
      .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault()
      ??throw new Exception("QA_CONFIG_NOT_AVAILABLE");
    Need(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase) &&
         cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"QA_ROOT_BAD");
    using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(cs));
    var db=provider.Obtener(eSistema.ITIL,(byte)1);
    Need(db.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)&&
         db.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase),
         "QA_WRONG_DATABASE");
    byte[] key=File.ReadAllBytes(Signer);
    Need(key.Length==32,"SIGNING_KEY_BAD");
    string selfSha=Hex(File.ReadAllBytes(Path.Combine(Root,"CaseLifecycleRead.cs")));
    string monthlySha=Hex(File.ReadAllBytes(Path.Combine(Monthly,"MonthEnd100Read.cs")));
    var keyRows=Q(db,PrimaryKeySql);
    var pk=new Dictionary<string,List<string>>(StringComparer.Ordinal);
    foreach(DataRow row in keyRows.Rows){
       string table=Val(row,"TableName");
       if(!pk.ContainsKey(table))pk[table]=new List<string>();
       pk[table].Add(Val(row,"ColumnName"));
    }
    var expected=new Dictionary<string,string[]>{
       ["taIncidente"]=new[]{"CodigoIncidente"},
       ["taIncidenteAtencion"]=new[]{"CodigoIncidente","Atencion"},
       ["taIncidenteDerivacion"]=new[]{"CodigoIncidente","NumeroDerivacion"},
       ["taIncidenteEncuesta"]=new[]{"CodigoIncidente"},
       ["taModulo"]=new[]{"CodigoModulo"},
       ["gnEstadoIncidente"]=new[]{"CodigoEstadoIncidente"}
    };
    foreach(var item in expected){
      Need(pk.ContainsKey(item.Key) &&
           pk[item.Key].SequenceEqual(item.Value,StringComparer.Ordinal),
           "QA_DECLARED_PRIMARY_KEY_SHAPE_NOT_AS_EXPECTED");
    }
    var fk=Q(db,FkSql);
    var fkMeta=new List<object>();
    foreach(DataRow row in fk.Rows){
       fkMeta.Add(new{
          parent_table=Val(row,"ParentTable"),target_table=Val(row,"TargetTable"),
          disabled=Convert.ToBoolean(row["Disabled"]),
          untrusted=Convert.ToBoolean(row["Untrusted"])
       });
    }
    // The observed incident/attention/derivation equality is NOT a FK
    // unless separately confirmed by live metadata above.
    var sourceReceipts=new List<object>();
    var values=new List<object>();
    var seen=new HashSet<string>(StringComparer.Ordinal);
    long totalAttention=0,totalDerivations=0,totalSurveys=0;
    int withAttention=0,withDerivation=0,withSurvey=0;
    int moduleMatched=0,stateMatched=0;
    for(int month=1;month<=9;month++){
       string ym="2026"+month.ToString("00",CultureInfo.InvariantCulture);
       var (source,sourceHash)=SignedSource(ym,monthlySha,key);
       DateTime start=new(2026,month,1),end=start.AddMonths(1);
       var rows=Q(db,FlowSql,"@start datetime,@end datetime",Window(start,end));
       Need(rows.Rows.Count==100,"FRESH_CASE_COUNT_DRIFT");
       sourceReceipts.Add(new{month=ym[..4]+"-"+ym[4..],receipt_sha256=sourceHash});
       for(int i=0;i<100;i++){
          var row=rows.Rows[i];
          var signed=source.RootElement.GetProperty("results")[i];
          long id=N(row,"CodigoIncidente");
          string caseHash=Sha(id.ToString(CultureInfo.InvariantCulture));
          Need(signed.GetProperty("case_sha256").GetString()==caseHash &&
               signed.GetProperty("module_code").GetString()==Val(row,"CodigoModulo").TrimEnd() &&
               signed.GetProperty("company").GetString()==Val(row,"CodigoEmpresa") &&
               signed.GetProperty("status_code").GetString()==Val(row,"CodigoEstadoIncidente"),
               "FRESH_LIFECYCLE_COHORT_SOURCE_DRIFT");
          Need(seen.Add(caseHash),"CROSS_MONTH_DUPLICATE_CASE");
          bool m=Convert.ToInt32(row["ModuleKeyMatched"])==1;
          bool s=Convert.ToInt32(row["StateKeyMatched"])==1;
          long a=N(row,"AttentionRows"),solved=N(row,"AttentionMarkedSolved"),
               finish=N(row,"AttentionHasFinish"),
               deriv=N(row,"DerivationRows"),survey=N(row,"SurveyRows");
          Need(a>=0&&a<=100&&solved>=0&&solved<=a&&finish>=0&&finish<=a&&
               deriv>=0&&deriv<=100&&survey>=0&&survey<=1,
               "LIFECYCLE_COUNTER_OUT_OF_BOUNDS");
          totalAttention+=a;totalDerivations+=deriv;totalSurveys+=survey;
          if(a>0)withAttention++;
          if(deriv>0)withDerivation++;
          if(survey>0)withSurvey++;
          if(m)moduleMatched++;
          if(s)stateMatched++;
          values.Add(new{
            month=ym[..4]+"-"+ym[4..],rank=i+1,
            case_sha256=caseHash,
            monthly_receipt_sha256=sourceHash,
            source="ELSE70/dbITIL_D/dbo.taIncidente",
            query_id="QA_ITIL_CASE_NATIVE_LIFECYCLE_BY_CODIGO_INCIDENTE",
            parent_rows=1,
            exact_key_equality_atencion=a,
            exact_key_equality_derivacion=deriv,
            exact_key_equality_encuesta=survey,
            atencion_solved_flag_count=solved,
            atencion_finish_date_count=finish,
            modulo_key_row_match=m,
            estado_key_row_match=s,
            codigo_estado_incidente=Val(row,"CodigoEstadoIncidente"),
            state_dictionary_atendido= row.IsNull("StateDictionaryAtendido") ?
                 (int?)null :Convert.ToInt32(row["StateDictionaryAtendido"]),
            db_declared_itil_to_ot_fk=false,
            business_resolution_certified=false,
            read_only=true
          });
       }
       source.Dispose();
    }
    Need(values.Count==900&&seen.Count==900,"LIFECYCLE_COUNT_INVALID");
    var receipt=new{
      schema=Schema,source_sha256=selfSha,worker="ELSE62",
      qa_server="ELSE70",qa_database="dbITIL_D",
      source="dbo.taIncidente",selected=900,months=9,
      source_receipts=sourceReceipts,
      pk_constraints=expected.Select(k=>new{table=k.Key,columns=k.Value}).OrderBy(x=>x.table),
      declared_fk_edges_observed=fkMeta,
      observed_key_equality_not_declaration_of_fk=true,
      cases_with_attention=withAttention,
      cases_with_derivation=withDerivation,
      cases_with_survey=withSurvey,
      cases_module_code_matched=moduleMatched,
      cases_state_code_matched=stateMatched,
      attention_rows=totalAttention,
      derivation_rows=totalDerivations,
      survey_rows=totalSurveys,
      results=values,read_only=true,
      business_modifications=0,causal_fixes_certified=0,
      read_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture)
    };
    byte[] content=JsonSerializer.SerializeToUtf8Bytes(receipt);
    string path=Path.Combine(Root,"itil_native_lifecycle_900.private.json");
    File.WriteAllBytes(path,content);
    string hash=Hex(content);
    File.WriteAllBytes(path+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
       schema=ProofSchema,source_sha256=selfSha,receipt_sha256=hash,
       hmac_sha256=Mac(Schema,selfSha,hash,key),read_only=true,worker="ELSE62"
    }));
    Console.WriteLine(JsonSerializer.Serialize(new{
        status="ITIL_NATIVE_LIFECYCLE_READ_SIGNED",selected=900,
        cases_with_attention=withAttention,cases_with_derivation=withDerivation,
        cases_with_survey=withSurvey,
        cases_module_code_matched=moduleMatched,cases_state_code_matched=stateMatched,
        attention_rows=totalAttention,derivation_rows=totalDerivations,
        survey_rows=totalSurveys,declared_fk_edges_observed=fkMeta.Count,
        business_fixes_certified=0,receipt_sha256=hash
    }));
    return 0;
  }catch(Exception ex){
    Console.Error.WriteLine("ITIL_NATIVE_LIFECYCLE_READ_FAILED:"+ex.GetType().Name+":"+ex.Message);
    return 3;
  }
 }
}
