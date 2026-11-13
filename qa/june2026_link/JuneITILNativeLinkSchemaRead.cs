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
using System.Xml.Linq;
using SIELSEAccesoDatos;

// Independent read-only system-catalog inspection of physical ITIL
// CodigoIncidente -> enterprise OT/Cobranza linking possibilities.
// No user records, SQL from notes, IDs, personal fields or writes.
internal static class JuneITILNativeLinkSchemaRead {
 const string Root=@"C:\Temp\ELSE_ITIL_JUNE_LINK_20261112";
 const string Signer=@"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private";
 const string Schema="else.itil.qa.2026-native-itil-business-link-metadata.v1";
 const string Proof="else.itil.qa.2026-native-itil-business-link-metadata-hmac.v1";
 static readonly string[] Databases={
 "dbITIL_D","dbComercial001_D","dbComercial003_D","dbComercial004_D",
 "dbComercial006_D","dbComercial007_D","dbComercial008_D",
 "dbComercial100_D","dbComercial200_D","dbComercial001_Diario",
 "dbComercial001_20230131","dbComercial003_mayo","dbGerencial_D","dbDistribucion_D"
 };
 static void Need(bool b,string reason){if(!b)throw new Exception(reason);}
 static string Hash(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
 static string Mac(byte[] key,string value)=>Convert.ToHexString(
   HMACSHA256.HashData(key,Encoding.UTF8.GetBytes(value))).ToLowerInvariant();
 static string Val(DataRow r,string col)=>r.IsNull(col)?"":Convert.ToString(r[col],CultureInfo.InvariantCulture)??"";
 static DataTable Q(AccesoDatos db,string query){
   var d=db.fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]",new SqlParameter[]{
     new("@stmt",SqlDbType.NVarChar,-1){Value=query},
     new("@params",SqlDbType.NVarChar,2){Value=""}
   });
   Need(d!=null&&d.Tables.Count>0,"NATIVE_LINK_METADATA_NO_RESULT");
   return d!.Tables[0];
 }
 static void Main(){
   Directory.CreateDirectory(Root);
   foreach(var e in new[]{"SIELSE_ACCESODATOS_KEY","SIELSE_CONEXION_DBSEGURIDAD"}){
      if(string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(e))){
         var value=Environment.GetEnvironmentVariable(e,EnvironmentVariableTarget.Machine);
         Need(!string.IsNullOrWhiteSpace(value),"NATIVE_LINK_CONFIG_MISSING");
         Environment.SetEnvironmentVariable(e,value);
      }
   }
   byte[] key=File.ReadAllBytes(Signer);Need(key.Length==32,"NATIVE_LINK_HMAC_KEY_MISSING");
   var x=XDocument.Load(@"D:\SitiosWeb\appsrvdev.else.com.pe\wApiSIELSESeguridad\www\web.config");
   string cs=x.Descendants("connectionStrings").Descendants("add")
       .Where(v=>(string?)v.Attribute("name")=="ConexionSIELSE")
       .Select(v=>(string?)v.Attribute("connectionString")).SingleOrDefault()
       ??throw new Exception("NATIVE_LINK_ROOT_NOT_FOUND");
   Need(cs.Contains("ELSE70",StringComparison.OrdinalIgnoreCase)
      &&cs.Contains("dbSeguridad_D",StringComparison.OrdinalIgnoreCase),"NATIVE_LINK_NOT_QA");
   using IConexionBD conn=new ConexionBD(new CadenaConexionCollection(cs));
   var itil=conn.Obtener(eSistema.ITIL,(byte)1);
   Need(itil.cdnConexion.NombreServidor.Equals("ELSE70",StringComparison.OrdinalIgnoreCase)
       &&itil.cdnConexion.NombreBaseDatos.Equals("dbITIL_D",StringComparison.OrdinalIgnoreCase),
       "NATIVE_LINK_NOT_ITIL_DATABASE");
   var active=Q(itil,@"SELECT name FROM sys.databases WHERE state_desc='ONLINE'
      AND name IN ('dbITIL_D','dbComercial001_D','dbComercial003_D',
      'dbComercial004_D','dbComercial006_D','dbComercial007_D',
      'dbComercial008_D','dbComercial100_D','dbComercial200_D',
      'dbComercial001_Diario','dbComercial001_20230131',
      'dbComercial003_mayo','dbGerencial_D','dbDistribucion_D')");
   var existing=new HashSet<string>(active.Rows.Cast<DataRow>().Select(r=>Val(r,"name")));
   var metadata=new List<object>();
   int directNativePairs=0;
   var issues=new List<object>();
   foreach(string database in Databases){
      if(!existing.Contains(database)){issues.Add(new{db=database,issue="DATABASE_NOT_ONLINE_VISIBLE"});continue;}
      try{
        var tbl=Q(itil,$@"SELECT s.name AS schema_name,t.name AS table_name,
          MAX(CASE WHEN c.name='CodigoIncidente' THEN 1 ELSE 0 END) AS itil_code,
          MAX(CASE WHEN c.name='CodigoOrdenTrabajo' THEN 1 ELSE 0 END) AS ot_code,
          MAX(CASE WHEN c.name='CodigoCobranza' THEN 1 ELSE 0 END) AS collection_code
          FROM [{database}].sys.tables t
          JOIN [{database}].sys.schemas s ON s.schema_id=t.schema_id
          JOIN [{database}].sys.columns c ON c.object_id=t.object_id
          WHERE c.name IN('CodigoIncidente','CodigoOrdenTrabajo','CodigoCobranza')
          GROUP BY s.name,t.name
          HAVING MAX(CASE WHEN c.name='CodigoIncidente' THEN 1 ELSE 0 END)=1
          ORDER BY s.name,t.name");
        var list=new List<object>();
        foreach(DataRow row in tbl.Rows){
          bool ot=Val(row,"ot_code")=="1";
          bool col=Val(row,"collection_code")=="1";
          if(ot||col)directNativePairs++;
          list.Add(new{
            schema=Val(row,"schema_name"),table=Val(row,"table_name"),
            has_itil_incident_named_column=true,
            has_ot_named_column=ot,has_cobranza_named_column=col,
            actual_fk_not_proven_by_column_names=true
          });
        }
        metadata.Add(new{database,tables_with_codigo_incidente=list,
          directly_coexisting_itil_and_business_columns=list.Count(x=>{
            var o=JsonSerializer.SerializeToElement(x);
            return o.GetProperty("has_ot_named_column").GetBoolean()||
                   o.GetProperty("has_cobranza_named_column").GetBoolean();})});
      }catch(Exception e){
        issues.Add(new{db=database,issue="METADATA_QUERY_FAILED",error=e.GetType().Name});
      }
   }
   var fks=Q(itil,@"SELECT fk.name AS fk_name,
      src.name AS source_table,dst.name AS referenced_table,
      sc.name AS source_column,dc.name AS referenced_column
      FROM sys.foreign_keys fk
      JOIN sys.tables src ON src.object_id=fk.parent_object_id
      JOIN sys.tables dst ON dst.object_id=fk.referenced_object_id
      JOIN sys.foreign_key_columns fc ON fc.constraint_object_id=fk.object_id
      JOIN sys.columns sc ON sc.object_id=fc.parent_object_id
                           AND sc.column_id=fc.parent_column_id
      JOIN sys.columns dc ON dc.object_id=fc.referenced_object_id
                           AND dc.column_id=fc.referenced_column_id
      WHERE src.name='taIncidente' OR dst.name='taIncidente'
      ORDER BY fk.name,sc.name");
   var fkRows=new List<object>();
   foreach(DataRow r in fks.Rows){
       fkRows.Add(new{
         source_table=Val(r,"source_table"),
         source_column=Val(r,"source_column"),
         referenced_table=Val(r,"referenced_table"),
         referenced_column=Val(r,"referenced_column")
       });
   }
   string srcHash=Hash(File.ReadAllBytes(Path.Combine(Root,"JuneITILNativeLinkSchemaRead.cs")));
   var report=new{
      schema=Schema,source_sha256=srcHash,qa_server="ELSE70",
      inspected_databases=metadata,
      direct_table_same_name_itil_and_ot_or_cobranza_pairs=directNativePairs,
      itil_taIncidente_foreign_keys=fkRows,
      failed_or_invisible_sources=issues,
      codigo_incidente_operativo_is_not_itil_codigo_incidente=true,
      native_business_fk_not_claimed_without_application_contract=true,
      read_only=true,write_count=0
   };
   byte[] raw=JsonSerializer.SerializeToUtf8Bytes(report);
   string digest=Hash(raw),dest=Path.Combine(Root,"native_itil_link_metadata.private.json");
   File.WriteAllBytes(dest,raw);
   File.WriteAllBytes(dest+".proof.json",JsonSerializer.SerializeToUtf8Bytes(new{
      schema=Proof,source_sha256=srcHash,receipt_sha256=digest,
      hmac_sha256=Mac(key,Schema+":"+srcHash+":"+digest),
      read_only=true
   }));
   Console.WriteLine(JsonSerializer.Serialize(new{
      status="NATIVE_ITIL_BUSINESS_SCHEMA_AUDIT_COMPLETE",
      databases_with_metadata=metadata.Count,direct_coexisting_pairs=directNativePairs,
      itil_declared_foreign_key_rows=fkRows.Count,
      metadata_errors=issues.Count,receipt_sha256=digest,write_count=0}));
 }
}
