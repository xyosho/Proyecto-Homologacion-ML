-- =============================================================================
-- 04_supabase_seguridad.sql — Solo para Supabase (PostgreSQL). Aplicado como migración "seguridad_rls".
-- Row Level Security activa en todas las tablas: la API pública (anon/authenticated) no puede leer ni
-- escribir hasta que se definan políticas explícitas (por ejemplo, lectura para el dashboard).
-- Ejemplo de política de solo lectura para usuarios autenticados (NO aplicada):
--   CREATE POLICY lectura_dashboard ON public.aspirante FOR SELECT TO authenticated USING (true);
-- =============================================================================
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['programa','tarifa_programa','beca','beneficio','entidad_financiera','periodo_academico','ubicacion',
                           'eps','canal_captacion','colegio','fondo_educacion_municipal','asesor','evento_captacion',
                           'inversion_captacion','aspirante','formulario_admision','contacto_emergencia','resultado_saber11',
                           'historial_bachillerato','nota_bachillerato','inscripcion','pregunta_entrevista','entrevista_admision',
                           'respuesta_entrevista','evaluacion_beca',
                           'documento_soporte','interaccion','seguimiento_academico']
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
  END LOOP;
END $$;

-- -----------------------------------------------------------------------------
-- Capa analítica: dataset_matricula (sql/05_dataset_matricula.sql). Migración "dataset_matricula_plano".
-- Es la ÚNICA tabla que la API pública puede leer, y solo leer: no tiene datos personales ni variables con
-- fuga. Python se conecta con la clave publicable guardada en .env o en los Secretos de Colab. Si esa clave
-- se filtrara, solo permitiría leer este dataset anonimizado; las otras 25 tablas siguen cerradas.
-- -----------------------------------------------------------------------------
ALTER TABLE public.dataset_matricula ENABLE ROW LEVEL SECURITY;
CREATE POLICY lectura_dataset_matricula ON public.dataset_matricula
    FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON public.dataset_matricula FROM anon, authenticated;            -- migración dataset_matricula_solo_lectura
GRANT SELECT ON public.dataset_matricula TO anon, authenticated;

-- Segunda tabla plana: dataset_permanencia (sql/06_dataset_permanencia.sql), migración "dataset_permanencia_plano".
-- Misma regla: solo lectura por la API, sin datos personales.
ALTER TABLE public.dataset_permanencia ENABLE ROW LEVEL SECURITY;
CREATE POLICY lectura_dataset_permanencia ON public.dataset_permanencia
    FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON public.dataset_permanencia FROM anon, authenticated;
GRANT SELECT ON public.dataset_permanencia TO anon, authenticated;

-- Tercera tabla plana: dataset_entrevista (sql/09_dataset_entrevista.sql), migración "entrevista_en_texto".
-- Las respuestas abiertas de la entrevista unidas por sección, sin nombres ni documentos: solo lectura (la usa el
-- modelo NLP en Colab). Las tablas de origen (pregunta, entrevista y respuesta) quedan cerradas: RLS activa, sin
-- política y sin permisos para anon ni authenticated.
ALTER TABLE public.dataset_entrevista ENABLE ROW LEVEL SECURITY;
CREATE POLICY lectura_dataset_entrevista ON public.dataset_entrevista
    FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON public.dataset_entrevista FROM anon, authenticated;
GRANT SELECT ON public.dataset_entrevista TO anon, authenticated;
REVOKE ALL ON public.pregunta_entrevista FROM anon, authenticated;
REVOKE ALL ON public.entrevista_admision FROM anon, authenticated;
REVOKE ALL ON public.respuesta_entrevista FROM anon, authenticated;

-- Sprint 5: resultado real de la campaña 2027-1 (migración "resultado_campana_2027_1"). Solo lectura.
ALTER TABLE public.resultado_campana_2027_1 ENABLE ROW LEVEL SECURITY;
CREATE POLICY lectura_resultado_campana ON public.resultado_campana_2027_1 FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON public.resultado_campana_2027_1 FROM anon, authenticated;
GRANT SELECT ON public.resultado_campana_2027_1 TO anon, authenticated;
