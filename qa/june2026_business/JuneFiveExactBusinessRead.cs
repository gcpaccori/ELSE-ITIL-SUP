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

// Five May-trained historical comparison cases. Never execute historical SQL.
// A ticket-to-business link is never a declared FK: only exact original-text
// identifier corroboration is considered; the signed historical note may be
// insufficient to prove the affected entity. Company 1 QA, fixed SELECT only.
internal static class JuneFiveExactBusinessRead {
 const string Root=@"C:\Temp\ELSE_ITIL_JUNE_BUSINESS2026_QA_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.2026-june5-exact-business-snapshot.v1";
 const string Proof="else.itil.qa.2026-june5-exact-business-snapshot-hmac.v1";
 const string ManifestSchema="else.itil.qa.2026-june5-selected-manifest.v1";
 const string ManifestProof="else.itil.qa.2026-june5-selected-manifest-hmac.v1";
 const string SourceName="JuneFiveExactBusinessRead.cs";
 static string Sha(string s)=>Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(s))).ToLowerInvariant();
 static string Hex(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
 static string Val(DataRow d,string name)=>d.IsNull(name)?"":Convert.ToString(d[name],CultureInfo.InvariantCulture)??"";
 static bool Has(DataRow d,string name)=>!string.IsNullOrEmpty(Val(d,name));
 static void Need(bool b,string e){if(!b)throw new Exception(e);}
 static DataTable Q(AccesoDatos db,string stmt,string param="",SqlParameter? value=null,SqlParameter? value2=null) {
   var args=new List<SqlParameter>{
     new("@stmt",SqlDbType.NVarChar,-1){Value=stmt},
     new("@params",SqlDbType.NVarChar,100){Value=param}
   };
   if(value!=null)args.Add(value);
   if(value2!=null)args.Add(value2);
   var dataset=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",args.ToArray());
   Need(dataset!=null&&dataset.Tables.Count>0,"QA_EMPTY_DATASET");
   return dataset!.Tables[0];
 }
 static object? Opt(DataRow d,string name) => d.IsNull(name)?null:d[name] is DateTime dt?dt.ToString("O",CultureInfo.InvariantCulture):Val(d,name);
 static JsonElement Prop(JsonElement e,string property)=>e.GetProperty(property);
 static string Value(JsonElement e,string name)=>e.GetProperty(name).GetString()??"";
 static bool ContainsToken(string text,string id)=>
   Regex.IsMatch(text,@"(?<!\d)"+Regex.Escape(id)+@"(?!\d)",RegexOptions.CultureInvariant);
 static string Extract(string s,string pattern) {
   var m=Regex.Match(s,pattern,RegexOptions.IgnoreCase|RegexOptions.Singleline|RegexOptions.CultureInvariant);
   return m.Success?m.Groups[1].Value:"";
 }
 static string ExtractTicketOt(string s) {
   var explicitId=Extract(s,@"\b(?:OT|orden(?:es)?\s+(?:de\s+)?trabajo)\b.{0,125}?\bN\s*[°ºo.]?\s*[:#=-]?\s*([0-9]{4,19})");
   if(explicitId!="")return explicitId;
   var nums=Regex.Matches(s,@"(?<!\d)\d{4,19}(?!\d)").Select(m=>m.Value).Distinct().ToArray();
   if(nums.Length==1 && Regex.IsMatch(s,@"\bOT\b|orden\s+de\s+trabajo",RegexOptions.IgnoreCase))return nums[0];
   return "";
 }
 static void Main(){
   Directory.CreateDirectory(Root);
   foreach(var key in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
     if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(key))){
       var env=Environment.GetEnvironmentVariable(key,EnvironmentVariableTarget.Machine);
       Need(!string.IsNullOrWhiteSpace(env),"QA_CONNECTOR_CONFIGURATION_MISSING");
       Environment.SetEnvironmentVariable(key,env);
     }
   }
   byte[] keyBytes=File.ReadAllBytes(Signer);
   Need(keyBytes.Length==32,"QA_HMAC_SIGNER_UNAVAILABLE");
   byte[] manifestBytes=File.ReadAllBytes(Path.Combine(Root,"june5_manifest.private.json"));
   using var mdoc=JsonDocument.Parse(manifestBytes);
   JsonElement manifest=mdoc.RootElement;
   using var pdoc=JsonDocument.Parse(File.ReadAllBytes(Path.Combine(Root,"june5_manifest.private.json.proof.json")));
   JsonElement mp=pdoc.RootElement;
   Need(Value(manifest,"schema")==ManifestSchema&&Value(mp,"schema")==ManifestProof,"MANIFEST_SCHEMA_INVALID");
   Need(Value(mp,"receipt_sha256")==Hex(manifestBytes)
       &&Value(mp,"hmac_sha256")==Convert.ToHexString(HMACSHA256.HashData(keyBytes,manifestBytes)).ToLowerInvariant(),
       "MANIFEST_HMAC_INVALID");
   int[] ranks={197,263,868,934,1065};
   var authorized=Prop(manifest,"rows").EnumerateArray().ToArray();
   Need(authorized.Length==5 && authorized.Select(x=>Prop(x,"rank").GetInt32()).SequenceEqual(ranks),
     "MANIFEST_WRONG_FIVE_RANKS");
   var xml=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   var root=xml.Descendants("connectionStrings").Descendants("add")
     .Where(x=>(string?)x.Attribute("name")=="ConexionSIELSE")
     .Select(x=>(string?)x.Attribute("connectionString")).SingleOrDefault();
   Need(!string.IsNullOrWhiteSpace(root)
     &&root.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)
     &&root.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"QA_ROOT_FORBIDDEN");
   using IConexionBD provider=new ConexionBD(new CadenaConexionCollection(root!));
   AccesoDatos itil=provider.Obtener(eSistema.ITIL,(byte)1);
   AccesoDatos commercial=provider.Obtener(eSistema.Comercial,(byte)1);
   Need(itil.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
       &&itil.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase)
       &&commercial.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
       &&commercial.cdnConexion.NombreBaseDatos.Equals("dbComercial001_D",StringComparison.OrdinalIgnoreCase),
       "QA_WRONG_DATABASE");
   const string sql=@"
WITH C AS (
 SELECT ROW_NUMBER() OVER (ORDER BY FechaSolicitud DESC,CodigoIncidente DESC) AS rank,
        CodigoIncidente,CodigoEmpresa,CodigoModulo,FechaSolicitud,
        DescripcionSolicitud,DescripcionSolucion,FechaRespuestaSolucion,FechaCierre
 FROM dbo.taIncidente
 WHERE FechaSolicitud>=@start AND FechaSolicitud<@end
)
SELECT * FROM C WHERE rank IN (197,263,868,934,1065) ORDER BY rank";
   DataTable incidents=Q(itil,sql,"@start datetime,@end datetime",
      new("@start",SqlDbType.DateTime){Value=new DateTime(2026,6,1)},
      new("@end",SqlDbType.DateTime){Value=new DateTime(2026,7,1)});
   Console.Error.WriteLine("ITIL_QUERY_ROWS="+incidents.Rows.Count+"; TABLES_COLUMN_COUNT="+incidents.Columns.Count);
   Need(incidents.Rows.Count==5,"ITIL_NOT_EXACT_FIVE_CASES");
   var outcomes=new List<object>();
   int exact=0,found=0,auditRows=0;
   for(int i=0;i<ranks.Length;i++){
     DataRow r=incidents.Rows[i];
     JsonElement signed=authorized[i];
     int rank=Convert.ToInt32(r["rank"]);
     string request=Val(r,"DescripcionSolicitud");
     string historical=Val(r,"DescripcionSolucion");
     Need(rank==ranks[i]&&Value(signed,"case_sha256")==Sha(Val(r,"CodigoIncidente"))
       &&Value(signed,"description_sha256")==Sha(request)
       &&Value(signed,"historical_solution_sha256")==Sha(historical)
       &&Value(signed,"module_code")==Val(r,"CodigoModulo").TrimEnd()
       &&Val(r,"CodigoEmpresa")=="1", "CASE_OR_REQUEST_OR_GOLD_HASH_DRIFT");
     string kind=(rank==934?"PADRON":rank==1065?"CAMPAIGN":"OT");
     string historicalId=rank switch {
       197 or 868 => Extract(historical,@"\bwhere\s+a\.CodigoOrdenTrabajo\s*=\s*'?([0-9]{4,19})"),
       934 => Extract(historical,@"\bwhere\s+a\.NumeroDNI\s*=\s*'([0-9]{8,12})'"),
       1065 => Extract(historical,@"\bwhere\s+a\.CodigoCampanaSupervision\s*=\s*'?([0-9]{4,19})"),
       _ => ""
     };
     string ticketId=rank==263?ExtractTicketOt(request):historicalId;
     if(rank==263 && ticketId=="")ticketId=Extract(request,@"\bOT\b.{0,120}?([0-9]{4,19})");
     if(rank!=263&&historicalId!=""&&ContainsToken(request,historicalId))ticketId=historicalId;
     if(rank!=263&&historicalId!=""&&!ContainsToken(request,historicalId))ticketId="";
     bool originalCorroborated=ticketId!=""&&ContainsToken(request,ticketId);
     string queryId=rank==934?historicalId:ticketId;
     bool historicalIdMatches=historicalId!=""&&originalCorroborated&&historicalId==ticketId;
     bool possibleQuery=queryId!=""&&Regex.IsMatch(queryId,@"^\d{4,19}$");
     if(rank==934 && queryId!="") possibleQuery=Regex.IsMatch(queryId,@"^\d{8,12}$");
     var audit=new List<object>();
     var current=new Dictionary<string,object?>();
     int objectRows=0;
     if(possibleQuery){
       if(kind=="OT"){
         long id=long.Parse(queryId,CultureInfo.InvariantCulture);
         const string otSql=@"SELECT TOP(2)
           CodigoOrdenTrabajo,CodigoEstadoOrdenTrabajo,CodigoSubEstadoOrdenTrabajo,
           CodigoTipoOrdenTrabajo,CodigoSubTipoOrdenTrabajo,CodigoCentroAtencion,
           FechaCreacion,FechaModificacion
           FROM dbo.taOrdenTrabajo WHERE CodigoOrdenTrabajo=@id";
         var table=Q(commercial,otSql,"@id bigint",new("@id",SqlDbType.BigInt){Value=id});
         Need(table.Rows.Count<=1,"OT_NOT_UNIQUE");
         objectRows=table.Rows.Count;
         if(objectRows==1)foreach(string col in new[]{"CodigoEstadoOrdenTrabajo","CodigoSubEstadoOrdenTrabajo",
           "CodigoTipoOrdenTrabajo","CodigoSubTipoOrdenTrabajo","CodigoCentroAtencion",
           "FechaCreacion","FechaModificacion"})current[col]=Opt(table.Rows[0],col);
         const string audSql=@"SELECT TOP(100)
           NombreCampo,ValorAnterior,ValorActual,FechaModificacion
           FROM dbo.taOrdenTrabajoAuditoriaCambio
           WHERE CodigoOrdenTrabajo=@id AND NombreCampo IN
           ('CodigoEstadoOrdenTrabajo','CodigoCentroAtencion','CodigoSubTipoOrdenTrabajo',
            'CodigoTipoOrdenTrabajo')
           ORDER BY FechaModificacion ASC";
         var aud=Q(commercial,audSql,"@id bigint",new("@id",SqlDbType.BigInt){Value=id});
         Need(aud.Rows.Count<=100,"OT_AUDIT_EXCEEDS_BOUND");
         foreach(DataRow a in aud.Rows){
           string name=Val(a,"NombreCampo");
           var timestamp=Opt(a,"FechaModificacion");
           var stamp=Val(a,"FechaModificacion");
           bool inJune=DateTime.TryParse(stamp,out var d)&&
             d>=new DateTime(2026,6,1)&&d<new DateTime(2026,7,1);
           audit.Add(new{field=name,before=Val(a,"ValorAnterior"),after=Val(a,"ValorActual"),
             at=timestamp,in_june=inJune,
             source="dbo.taOrdenTrabajoAuditoriaCambio",independent_execution_trace_unproven=true});
         }
         const string auditModSql=@"SELECT TOP(100)
           NombreCampo,ValorAnterior,ValorActual,FechaModificacion
           FROM dbo.taOrdenTrabajo_ModificacionIN
           WHERE CodigoOrdenTrabajo=@id
             AND NombreCampo IN ('CodigoEstadoOrdenTrabajo','CodigoCentroAtencion',
                  'CodigoSubTipoOrdenTrabajo','CodigoTipoOrdenTrabajo')
           ORDER BY FechaModificacion ASC";
         var modified=Q(commercial,auditModSql,"@id bigint",new("@id",SqlDbType.BigInt){Value=id});
         Need(modified.Rows.Count<=100,"OT_MODIFICATION_IN_EXCEEDS_BOUND");
         foreach(DataRow a in modified.Rows){
           string name=Val(a,"NombreCampo");
           string stamp=Val(a,"FechaModificacion");
           bool inJune=DateTime.TryParse(stamp,out var d)&&
              d>=new DateTime(2026,6,1)&&d<new DateTime(2026,7,1);
           audit.Add(new{field=name,before=Val(a,"ValorAnterior"),after=Val(a,"ValorActual"),
             at=Opt(a,"FechaModificacion"),in_june=inJune,
             source="dbo.taOrdenTrabajo_ModificacionIN",independent_execution_trace_unproven=true});
         }
       } else if(kind=="PADRON") {
         const string sqlPadron=@"SELECT TOP(2)
           CodigoPadronRUC,ApellidoPaterno,RazonSocial,FechaCreacion,FechaModificacion
           FROM dbo.taPadronRuc WHERE NumeroDNI=@dni";
         var table=Q(commercial,sqlPadron,"@dni varchar(12)",
           new("@dni",SqlDbType.VarChar,12){Value=queryId});
         // Customer lookups are not guaranteed unique, and may contain multiple
         // entities; do not pick one silently.
         objectRows=table.Rows.Count;
         string expected=Extract(historical,@"\bApellidoPaterno\s*=\s*'([^']{2,80})'");
         if(objectRows==1){
           current["surname_matches_note_target"]=string.Equals(Val(table.Rows[0],"ApellidoPaterno").Trim(),
             expected.Trim(),StringComparison.OrdinalIgnoreCase);
           current["surname_matches_request_target"]=Regex.IsMatch(request,
             @"\bPINEDA\b",RegexOptions.IgnoreCase)
             &&string.Equals(Val(table.Rows[0],"ApellidoPaterno").Trim(),"PINEDA",StringComparison.OrdinalIgnoreCase);
           current["FechaCreacion"]=Opt(table.Rows[0],"FechaCreacion");
           current["FechaModificacion"]=Opt(table.Rows[0],"FechaModificacion");
         }
       } else if(kind=="CAMPAIGN"){
         long id=long.Parse(queryId,CultureInfo.InvariantCulture);
         const string campSql=@"SELECT TOP(2)
          CodigoCampanaSupervision,CodigoEstadoCampanaSupervision,FechaInicio,FechaFin,
          FechaCreacion,FechaModificacion FROM dbo.taCampanaSupervision
          WHERE CodigoCampanaSupervision=@id";
         var table=Q(commercial,campSql,"@id bigint",new("@id",SqlDbType.BigInt){Value=id});
         Need(table.Rows.Count<=1,"CAMPAIGN_ID_NOT_UNIQUE");
         objectRows=table.Rows.Count;
         if(objectRows==1)foreach(string col in new[]{"CodigoEstadoCampanaSupervision",
           "FechaInicio","FechaFin","FechaCreacion","FechaModificacion"})
           current[col]=Opt(table.Rows[0],col);
       }
     }
     string targetField=rank switch{
       197=>"CodigoCentroAtencion",
       868=>"CodigoEstadoOrdenTrabajo",
       1065=>"CodigoEstadoCampanaSupervision",
       934=>"ApellidoPaterno",
       263=>"CodigoSubTipoOrdenTrabajo",
       _=>""};
     string expectedCode=(rank==934||rank==263)?"":Extract(historical,
       @"\b"+Regex.Escape(targetField)+@"\s*=\s*([0-9]{1,6})");
     bool juneTrace=false,expectedTrace=false;
     foreach(var ob in audit){
       var d=JsonSerializer.SerializeToElement(ob);
       bool match=d.GetProperty("field").GetString()==targetField&&d.GetProperty("in_june").GetBoolean();
       juneTrace|=match;
       expectedTrace|=match&&expectedCode!=""&&d.GetProperty("after").GetString()==expectedCode;
     }
     exact+=originalCorroborated?1:0;
     found+=objectRows==1?1:0;
     auditRows+=audit.Count;
     outcomes.Add(new {
       rank,case_sha256=Value(signed,"case_sha256"),source_month="2026-06",
       module_code=Value(signed,"module_code"),kind,
       original_request_id_corrobated=originalCorroborated,
       historical_note_identifier_present=historicalId!="",
       request_and_note_id_match=historicalIdMatches,
       identifier_only_from_historical_note=historicalId!=""&&!originalCorroborated,
       identifier_sha256=possibleQuery?Sha(queryId):"",
       identifier_private=possibleQuery?queryId:"",
       business_table=kind=="OT"?"dbo.taOrdenTrabajo":kind=="PADRON"?"dbo.taPadronRuc":"dbo.taCampanaSupervision",
       business_row_count=objectRows,business_row_unique=objectRows==1,
       target_field=targetField,historical_target_code=expectedCode,
       current_snapshot=current,
       order_audit_events=audit,
       audit_event_count=audit.Count,
       june_exact_field_audit_seen=juneTrace,
       june_exact_field_audit_matches_historical_target=expectedTrace,
       sql_temporal_snapshot_available=false,
       same_case_full_historical_before_after_certified=false,
       historical_note_sql_was_executed_certified=false,
       action_executed_by_agent=false,
       repair_certified=false
     });
   }
   var tableAvailability=new Dictionary<string,bool>();
   foreach(string table in new[]{"dbo.taOrdenTrabajo","dbo.taPadronRuc","dbo.taCampanaSupervision"}){
      string fixedSql=table switch{
        "dbo.taOrdenTrabajo"=>"SELECT TOP(1) 1 AS available FROM dbo.taOrdenTrabajo",
        "dbo.taPadronRuc"=>"SELECT TOP(1) 1 AS available FROM dbo.taPadronRuc",
        _=>"SELECT TOP(1) 1 AS available FROM dbo.taCampanaSupervision"};
      tableAvailability[table]=Q(commercial,fixedSql).Rows.Count==1;
   }
   var output=new {
    schema=Schema,qa_itil="ELSE70/dbITIL_D",qa_business="ELSE70/dbComercial001_D",
    source_sha256=Hex(File.ReadAllBytes(Path.Combine(Root,SourceName))),
    read_utc=DateTime.UtcNow.ToString("O",CultureInfo.InvariantCulture),
    business_table_has_any_rows=tableAvailability,
    selected_ranks=ranks,original_five_manifest_sha256=Hex(manifestBytes),
    cohort_source_receipt_sha256=Value(manifest,"june_source_receipt_sha256"),
    cohort_history_receipt_sha256=Value(manifest,"june_history_receipt_sha256"),
    actual_five_source_sha256=Hex(File.ReadAllBytes(Path.Combine(Root,SourceName))),
    selected=5,verified_source_ticket_sha256_matches=5,verified_history_sha256_matches=5,
    source_ids_corrobated_from_request=exact,unique_business_records_found=found,
    audit_events_loaded=auditRows,
    table_temporal_asof_available=false,fixes_historically_proven=0,
    business_modifications=0,read_only=true,rows=outcomes
   };
   var receipt=JsonSerializer.SerializeToUtf8Bytes(output);
   var outpath=Path.Combine(Root,"june5_exact_business.private.json");
   File.WriteAllBytes(outpath,receipt);
   string hash=Hex(receipt),source=output.actual_five_source_sha256;
   var mac=Convert.ToHexString(HMACSHA256.HashData(keyBytes,
      Encoding.UTF8.GetBytes(Schema+":"+source+":"+hash))).ToLowerInvariant();
   File.WriteAllBytes(outpath+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
     schema=Proof,worker="ELSE62",source_sha256=source,
     receipt_sha256=hash,hmac_sha256=mac,read_only=true
   }));
   Console.WriteLine(JsonSerializer.Serialize(new{
     status="JUNE5_BUSINESS_QA_FINISHED",cases=outcomes.Count,
     exact_ids_from_original_request=exact,unique_business_rows=found,audit_rows=auditRows,
     current_is_not_June_asof=true,certified_repair=0,
     receipt_sha256=hash,source_sha256=source
   }));
 }
}
