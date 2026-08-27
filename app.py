import streamlit as st
from datetime import datetime, timezone
import db

# Configuració de la pàgina
st.set_page_config(page_title="Gestió de Tasques i Suport", page_icon="⏱️", layout="centered")

# Control de sessió
if "usuario" not in st.session_state:
    st.session_state.usuario = None

# --- COMPTADOR EN VIU ---
@st.fragment(run_every="1s")
def mostrar_comptador_en_viu(fecha_inicio):
    inicio = fecha_inicio
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    
    ahora = datetime.now(timezone.utc)
    diferencia = ahora - inicio
    
    segons_totals = max(0, int(diferencia.total_seconds()))
    horas, rem = divmod(segons_totals, 3600)
    minutos, segundos = divmod(rem, 60)
    
    st.metric(
        label="Temps dedicat en aquesta tasca:",
        value=f"{horas:02d}:{minutos:02d}:{segundos:02d}"
    )

# --- PANTALLA DE LOGIN ---
if not st.session_state.usuario:
    st.title("🔑 Iniciar Sessió")
    
    with st.form("form_login"):
        nombre = st.text_input("Usuari (Nom):", value="")
        password = st.text_input("Contrasenya:", type="password")
        btn_login = st.form_submit_button("Entrar", use_container_width=True)
        
        if btn_login:
            user = db.obtener_usuario_por_nombre(nombre)
            if user and db.verificar_password(password, user['password_hash']):
                st.session_state.usuario = user
                st.rerun()
            else:
                st.error("Usuari o contrasenya incorrectes.")

# --- PANTALLA PRINCIPAL ---
else:
    user = st.session_state.usuario
    
    with st.sidebar:
        st.write(f"👤 **{user['nombre']}**")
        rol_traduit = "Participant" if user['rol'] == 'empleado' else "Coordinació"
        st.caption(f"Rol: {rol_traduit}")
        st.divider()
        if st.button("Tancar Sessió", use_container_width=True):
            st.session_state.usuario = None
            st.rerun()

    # Vista Participant (Mònica)
    if user['rol'] == 'empleado':
        st.title("⏱️ Registre de Tasques i Temps")

        # --- RESUM DEL MES ACTUAL ---
        horas_mes, tarifa_mes = db.obtener_resumen_mes_actual(user['id'])
        importe_mes = horas_mes * tarifa_mes

        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Temps dedicat aquest mes", f"{horas_mes:.2f} h")
        
        if tarifa_mes > 0:
            col_m2.metric("Compensació estimada", f"{importe_mes:.2f} €", help=f"Acordat a {tarifa_mes:.2f} €/h")
        else:
            col_m2.metric("Compensació estimada", "Pendent d'acordar", help="Encara no s'ha definit la compensació per hora per a aquest mes.")

        st.divider()

        # --- GESTIÓ DE TASCA ACTIVA ---
        jornada_activa = db.obtener_jornada_activa(user['id'])

        if jornada_activa:
            st.warning("🔴 **Tasca en curs**")
            
            mostrar_comptador_en_viu(jornada_activa['fecha_inicio'])

            if st.button("🔴 Finalitzar Tasca", type="primary", use_container_width=True):
                db.finalizar_jornada(jornada_activa['id'])
                st.success("Tasca finalitzada correctament.")
                st.rerun()

        else:
            st.info("⚪ No hi ha cap tasca activa en aquest moment.")
            if st.button("🟢 Iniciar Tasca", type="primary", use_container_width=True):
                db.iniciar_jornada(user['id'])
                st.success("Tasca iniciada.")
                st.rerun()

        st.divider()

        # Historial
        st.subheader("📋 Historial de Tasques")
        historial = db.obtener_historial_fichajes(user['id'])
        
        if historial:
            st.dataframe(
                historial, 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.caption("No hi ha tasques finalitzades registrades.")

    # Vista Coordinació (Jaume)
    elif user['rol'] == 'jefe':
        st.title("👨‍💼 Resum i Compensacions")

        # 1. Filtres
        empleados = db.obtener_empleados()
        if not empleados:
            st.warning("No hi ha usuaris registrats al sistema.")
        else:
            col_emp, col_mes, col_any = st.columns(3)
            
            with col_emp:
                emp_nombres = {emp['id']: emp['nombre'] for emp in empleados}
                emp_id = st.selectbox("Seleccionar persona:", options=list(emp_nombres.keys()), format_func=lambda x: emp_nombres[x])
            
            with col_mes:
                meses_cat = {1: "Gener", 2: "Febrer", 3: "Març", 4: "Abril", 5: "Maig", 6: "Juny", 7: "Juliol", 8: "Agost", 9: "Setembre", 10: "Octubre", 11: "Novembre", 12: "Desembre"}
                mes_sel = st.selectbox("Mes:", options=list(meses_cat.keys()), index=7, format_func=lambda x: meses_cat[x])
            
            with col_any:
                any_sel = st.number_input("Any:", min_value=2024, max_value=2030, value=2026)

            st.divider()

            # 2. Acord de valor per hora
            tarifa_actual = float(db.obtener_tarifa_mes(emp_id, any_sel, mes_sel))
            
            col_tarifa, col_btn_tarifa = st.columns([2, 1])
            with col_tarifa:
                nueva_tarifa = st.number_input("Compensació per hora (€/h):", min_value=0.0, value=tarifa_actual, step=0.5, format="%.2f")
            with col_btn_tarifa:
                st.write("")
                st.write("")
                if st.button("Guardar Acord", use_container_width=True):
                    db.guardar_tarifa_mes(emp_id, any_sel, mes_sel, nueva_tarifa)
                    st.success("Compensació per hora actualitzada.")
                    st.rerun()

            # 3. Consulta i càlculs
            fichajes_mes = db.obtener_fichajes_mes(emp_id, any_sel, mes_sel)
            
            total_horas = sum([float(f['Hores']) for f in fichajes_mes]) if fichajes_mes else 0.0
            precio_hora_float = float(nueva_tarifa)
            total_importe = total_horas * precio_hora_float

            # 4. Mètriques
            m1, m2, m3 = st.columns(3)
            m1.metric("Temps Total", f"{total_horas:.2f} h")
            m2.metric("Acord per Hora", f"{precio_hora_float:.2f} €/h")
            m3.metric("Total Acordat", f"{total_importe:.2f} €")

            st.divider()

            # 5. Taula de detalls
            st.subheader(f"📋 Detall de tasques - {meses_cat[mes_sel]} {any_sel}")
            if fichajes_mes:
                st.dataframe(fichajes_mes, use_container_width=True, hide_index=True)
            else:
                st.info(f"No hi ha registres de activitat per a {emp_nombres[emp_id]} el mes de {meses_cat[mes_sel]} de {any_sel}.")