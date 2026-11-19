"""Static self-service HTML/CSS/JS for *loopback-only* guided canary.

No third-party resources, network origins, cookies, localStorage or analytics.
All dynamic incident and response text is inserted via textContent, never HTML.
Tokens live solely in a password field for the current browser page lifetime.
"""
from __future__ import annotations

HTML = """<!doctype html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ELSE-ITIL · Asistencia guiada</title>
<link rel="stylesheet" href="/v1/support/ui.css">
</head><body>
<main class="shell">
<header class="mast">
  <div class="kicker">ELSE-ITIL / MESA DE AYUDA</div>
  <h1>Encuentra el siguiente paso.</h1>
  <p>Describe lo que ves. Recibirás una comprobación sencilla y podrás preparar un
  resumen para soporte sin cambiar sistemas.</p>
  <p class="caution">Piloto privado supervisado · No certifica diagnósticos ni
  repara problemas · No ingreses contraseñas corporativas ni datos personales.</p>
</header>
<div class="columns">
<section class="panel" aria-labelledby="newcase">
  <h2 id="newcase">1. Cuéntanos qué sucede</h2>
  <label for="token">Token de acceso del piloto <span class="small">(no es tu contraseña corporativa)</span></label>
  <input id="token" type="password" autocomplete="off" spellcheck="false"
   minlength="32" maxlength="256" placeholder="Token proporcionado por soporte">
  <label for="case_ref">Referencia del caso</label>
  <input id="case_ref" minlength="4" maxlength="80" required
   placeholder="Ej.: SOLICITUD-0001" autocomplete="off">
  <label for="service">Aplicación o servicio</label>
  <input id="service" maxlength="90" placeholder="Ej.: Portal de oficina" autocomplete="off">
  <label for="description">¿Qué aparece en tu pantalla?</label>
  <textarea id="description" rows="5" maxlength="1400"
    placeholder="Explícalo con tus palabras sin colocar nombres, claves ni documentos."></textarea>
  <button id="start" class="primary" type="button">Comenzar orientación</button>
  <p class="small">La referencia permite recuperar la misma conversación al volver a
  introducir exactamente la misma descripción. No se recopilan datos corporativos automáticamente.</p>
</section>
<section class="panel conversation" aria-labelledby="dialog">
  <h2 id="dialog">2. Tu orientación</h2>
  <p id="status" class="status" role="status" aria-live="polite">Sin conversación iniciada.</p>
  <div class="stage" id="stage">Pendiente</div>
  <div id="answer" class="answer">Aquí aparecerá una comprobación segura y qué observar.</div>
  <label for="reply">¿Qué observaste? <span class="small">(solo datos no sensibles)</span></label>
  <textarea id="reply" rows="3" maxlength="1400"
     placeholder="Ej.: aparece el aviso al entrar; no entiendo la indicación..."></textarea>
  <div class="actions">
    <button id="continue" type="button" disabled>Enviar observación</button>
    <button id="history" class="secondary" type="button" disabled>Ver mi historial</button>
  </div>
  <div class="quick-feedback" aria-label="Respuestas rápidas">
    <button type="button" data-feedback="Vi la primera opción que me indicaste en la pantalla.">Opción A</button>
    <button type="button" data-feedback="Vi la segunda opción que me indicaste en la pantalla.">Opción B</button>
    <button type="button" data-feedback="No entiendo cómo realizar ese paso desde la pantalla.">No entiendo</button>
    <button type="button" data-feedback="Sigue fallando y no tengo permisos para hacer cambios.">Sigue fallando</button>
    <button type="button" data-feedback="Ahora funciona la operación que antes fallaba.">Ya funciona</button>
  </div>
  <pre id="timeline" class="timeline" aria-live="polite"></pre>
</section>
<section class="panel handoff" aria-labelledby="share">
  <h2 id="share">3. Si necesitas a soporte</h2>
  <p>El resumen contiene tus observaciones y los pasos guiados, <strong>no una causa
  confirmada</strong>. Revísalo antes de entregarlo por un canal autorizado.</p>
  <label class="consent">
    <input id="consent" type="checkbox">
    He revisado lo que escribí y autorizo generar un resumen para compartir con soporte.
  </label>
  <label class="consent">
    <input id="privacy" type="checkbox">
    Entiendo que debo omitir contraseñas, documentos y datos privados.
  </label>
  <button id="handoff" class="primary" type="button" disabled>Preparar entrega a soporte</button>
  <label for="package">Paquete firmado para soporte <span class="small">(válido durante 72 horas)</span></label>
  <textarea id="package" rows="5" readonly placeholder="Aparecerá aquí cuando lo autorices."></textarea>
  <div class="actions">
    <button id="copy" type="button" disabled>Copiar paquete</button>
    <button id="revoke" class="secondary" type="button" disabled>Revocar paquete</button>
    <button id="revoke_all" class="secondary" type="button" disabled>Revocar todas las entregas</button>
  </div>
  <p class="small">El equipo autorizado puede verificar el recibo y preparar
  comprobaciones técnicas independientes. No hay envío automático ni acceso a sistemas
  de negocio. Revocar invalida el recibo para futuras verificaciones.</p>
</section>
</div>
<footer>ELSE-ITIL · Diagnóstico orientativo · Servicio privado, sin reparaciones automáticas</footer>
</main>
<script src="/v1/support/ui.js" defer></script>
</body></html>"""

CSS = """
:root{font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;
 color-scheme:light;color:#162837;background:#f5f7fa}
*{box-sizing:border-box}
body{margin:0}
.shell{max-width:1360px;margin:0 auto;padding:28px 22px 42px}
.mast{padding:18px 12px 30px}
.kicker{font-size:.78rem;letter-spacing:.14em;font-weight:800;color:#245e78}
h1{font-size:clamp(2rem,3.4vw,3.4rem);letter-spacing:-.035em;margin:.18em 0}
h2{font-size:1.15rem;letter-spacing:-.02em;margin:0 0 20px}
p{line-height:1.52}
.mast>p{max-width:740px;color:#4a6070;margin:.4em 0}
.caution{font-size:.9rem;font-weight:600}
.columns{display:grid;grid-template-columns:1fr 1.13fr 1fr;gap:18px}
.panel{background:#fff;border:1px solid #e0e8ee;border-radius:16px;
 padding:25px 23px;box-shadow:0 4px 20px #16384d0b;min-width:0}
label{display:block;font-size:.91rem;font-weight:700;margin:18px 0 7px}
input,textarea{display:block;width:100%;padding:11px 12px;font:inherit;font-size:.96rem;
 background:#fcfdfe;border:1px solid #bccdd7;border-radius:8px;color:#173044}
textarea{resize:vertical;min-height:68px}
input:focus-visible,textarea:focus-visible,button:focus-visible{
 outline:3px solid #87b7d4;outline-offset:2px}
button{font:inherit;font-weight:750;border:1px solid #2d667f;border-radius:8px;
 padding:11px 14px;cursor:pointer;background:#e9f3f8;color:#15465b;margin-top:12px}
button.primary{background:#165c78;color:white}
button.secondary{border-color:#c9d9e1;background:#f6f9fb;color:#35576a}
button:hover:not(:disabled){filter:brightness(.96)}
button:disabled{cursor:not-allowed;opacity:.44}
.small{font-size:.78rem;font-weight:400;color:#5d707d}
.status{padding:10px 12px;font-size:.85rem;background:#edf5f9;
 border-radius:8px;overflow-wrap:anywhere}
.stage{font-size:.8rem;letter-spacing:.03em;color:#2f657e;
 font-weight:800;margin:16px 0 10px}
.answer{white-space:pre-wrap;overflow-wrap:anywhere;background:#f9fbfc;
 border-left:3px solid #277a9a;border-radius:5px;padding:16px;
 min-height:180px;line-height:1.65;font-size:.92rem}
.actions{display:flex;gap:9px;flex-wrap:wrap}
.timeline{font-family:inherit;white-space:pre-wrap;overflow-wrap:anywhere;
 font-size:.82rem;line-height:1.65;color:#455f6b}
.consent{display:flex;align-items:flex-start;gap:9px;font-weight:500;
 font-size:.87rem;line-height:1.5}
.quick-feedback{display:flex;gap:5px;flex-wrap:wrap;margin-top:10px}
.quick-feedback button{margin-top:4px;font-size:.78rem;padding:7px 9px;border-color:#d3dfe7}
.consent input{width:18px;min-width:18px;margin-top:2px}
#package{font-family:ui-monospace,SFMono-Regular,monospace;font-size:.73rem;
 min-height:112px;overflow-wrap:anywhere}
footer{text-align:center;color:#627786;font-size:.77rem;margin:35px 0 0}
@media(max-width:1100px){.columns{grid-template-columns:1fr 1fr}.handoff{grid-column:span 2}}
@media(max-width:720px){.columns{grid-template-columns:1fr}.handoff{grid-column:span 1}.shell{padding:12px}.panel{padding:19px}}
"""

JS = r"""
"use strict";
(() => {
  const e = id => document.getElementById(id);
  let sid = null;
  let nextTurn = null;
  let currentReceipt = null;
  const str = v => typeof v === "string" ? v : "";
  const status = message => { e("status").textContent = message; };
  const busy = active => {
    e("start").disabled = active;
    e("continue").disabled = active || !sid || !nextTurn;
    e("history").disabled = active || !sid;
    e("handoff").disabled = active || !sid;
    e("revoke").disabled = active || !currentReceipt;
    e("revoke_all").disabled = active || !sid;
  };
  async function api(path, method="GET", payload=null) {
    const token = e("token").value.trim();
    if (token.length < 32 || token.length > 256) {
      throw new Error("Ingresa el token privado de acceso al piloto (no tu contraseña corporativa).");
    }
    const opts = {
      method, cache:"no-store", credentials:"omit", redirect:"error",
      headers:{"Authorization":"Bearer " + token}
    };
    if (payload !== null) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(payload);
    }
    const response = await fetch(path, opts);
    let data = {};
    try { data = await response.json(); }
    catch (_ignored) { throw new Error("Respuesta incompleta del servicio."); }
    if (!response.ok) {
      if (response.status === 429) throw new Error("Servicio ocupado. Vuelve a intentarlo.");
      if (response.status === 401) throw new Error("El token de acceso no fue aceptado.");
      throw new Error("Solicitud rechazada (" + response.status + "): " + str(data.error));
    }
    return data;
  }
  const show = response => {
    if (typeof response.session_id === "string") sid = response.session_id;
    if (Object.hasOwn(response, "next_turn")) nextTurn = response.next_turn;
    const view = response.presentacion_para_usuario || {};
    e("stage").textContent = str(view.etapa).replaceAll("_"," ") || "ORIENTACIÓN";
    e("answer").textContent = str(view.respuesta_sencilla) || "No se pudo generar una indicación segura. Contacta a soporte.";
    status(response.replayed ? "Turno recuperado, sin repetir diagnóstico." :
      "Turno " + response.turn + " guardado. " +
      (response.quality?.accepted ? "Guía revisada por controles automáticos." :
       "Este resultado necesita revisión humana."));
    busy(false);
  };
  async function operation(f) {
    busy(true);
    try { await f(); }
    catch (err) { status(err instanceof Error ? err.message : "No se pudo realizar la acción."); }
    finally { busy(false); }
  }
  e("start").addEventListener("click", () => operation(async () => {
    const req = {
      case_ref:e("case_ref").value.trim(),
      input_scope:"requester_submitted",
      service:e("service").value.trim() || "DESCONOCIDO",
      description:e("description").value.trim(),
    };
    if (req.description.length < 15) throw new Error("Describe lo que ves con un poco más de detalle.");
    const result = await api("/v1/support/guided/start","POST",req);
    currentReceipt = null;
    e("package").value = "";
    e("copy").disabled = true;
    show(result);
  }));
  document.querySelectorAll("[data-feedback]").forEach(button => {
    button.addEventListener("click", () => {
      e("reply").value = button.getAttribute("data-feedback") || "";
      e("reply").focus();
    });
  });
  e("continue").addEventListener("click", () => operation(async () => {
    if (!sid || !nextTurn) throw new Error("Primero inicia o recupera un caso.");
    const reply = e("reply").value.trim();
    if (reply.length < 5) throw new Error("Describe qué observaste antes de continuar.");
    const result = await api("/v1/support/guided/continue","POST",{
      session_id:sid,expected_turn:nextTurn,reply
    });
    e("reply").value = "";
    show(result);
  }));
  e("history").addEventListener("click", () => operation(async () => {
    if (!sid) return;
    const data = await api("/v1/support/guided/case/" + sid);
    let lines = ["SERVICIO: " + str(data.service),
      "ESTADO: " + str(data.current_stage).replaceAll("_"," "),
      "EVIDENCIA CORPORATIVA: sin vincular"];
    for (const o of data.observations || []) {
      lines.push("TURNO " + o.turn +
        "\n  Lo que reportaste: " + str(o.reported_by_user) +
        "\n  Comprobación sugerida: " + str(o.safe_screen_check) +
        "\n  Modelo aceptado por formato: " + (o.model_format_accepted ? "sí" : "no"));
    }
    e("timeline").textContent = lines.join("\n");
    status("Historial privado recuperado; no es una certificación de causa.");
  }));
  e("handoff").addEventListener("click", () => operation(async () => {
    if (!sid) throw new Error("Primero inicia un caso.");
    if (!e("consent").checked || !e("privacy").checked) {
      throw new Error("Antes de generar el paquete, debes autorizarlo y revisar la advertencia de privacidad.");
    }
    const result = await api("/v1/support/guided/handoff","POST",{
      session_id:sid,consent_to_share:true,privacy_notice_acknowledged:true
    });
    e("package").value = JSON.stringify(result,null,2);
    currentReceipt = str(result.packet?.receipt_id);
    e("copy").disabled = false;
    status("Paquete firmado creado. Revísalo y envíalo solo por un canal autorizado a soporte.");
  }));
  e("copy").addEventListener("click", async () => {
    try {
      if (!e("package").value) return;
      await navigator.clipboard.writeText(e("package").value);
      status("Paquete copiado. No lo publiques; entrégalo únicamente al equipo autorizado.");
    } catch (_err) { status("Selecciona y copia manualmente el texto del paquete."); }
  });
  e("revoke_all").addEventListener("click", () => operation(async () => {
    if (!sid) return;
    const result = await api("/v1/support/guided/revoke-all","POST",{
      session_id:sid
    });
    currentReceipt = null;
    e("package").value = "";
    e("copy").disabled = true;
    status("Se revocaron " + result.revoked_count + " entregas. "
      + "Los archivos ya compartidos no se borran, pero dejarán de verificarse como válidos.");
  }));
  e("revoke").addEventListener("click", () => operation(async () => {
    if (!sid || !currentReceipt) return;
    await api("/v1/support/guided/revoke","POST",{
      session_id:sid,receipt_id:currentReceipt
    });
    currentReceipt = null;
    e("package").value = "";
    e("copy").disabled = true;
    status("Entrega revocada; el recibo ya no superará las verificaciones futuras.");
  }));
})();
"""
