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
                           'historial_bachillerato','nota_bachillerato','inscripcion','evaluacion_beca','documento_soporte','interaccion',
                           'seguimiento_academico']
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
