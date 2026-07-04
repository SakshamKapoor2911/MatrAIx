import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { DigitalGlobe } from "./studio/DigitalGlobe";
import { StudioMeshShell } from "./studio/StudioShell";

export interface HomeViewProps {
  onOpenPersonaEval: () => void;
}

export function HomeView({ onOpenPersonaEval }: HomeViewProps) {
  return (
    <StudioMeshShell>
      <div className="custom-scrollbar flex min-h-0 flex-1 flex-col items-center justify-center px-6 py-10">
        <div className="landing-home-hero landing-fade-up mx-auto flex w-full max-w-[520px] flex-col items-center text-center">
          <div className="landing-home-globe mb-2" aria-hidden>
            <DigitalGlobe />
          </div>

          <p className="hud mt-2 text-[10px] text-primary">PersonaBench</p>

          <div className="landing-stat-block mt-4 items-center">
            <span className="landing-stat-value landing-stat-value--home">8.3B</span>
            <span className="landing-stat-label">personas</span>
          </div>

          <h1 className="landing-home-title mt-5">
            Planetary-scale{" "}
            <span className="landing-home-title-accent">digital humans</span>
          </h1>

          <p className="mt-4 max-w-md text-[14px] leading-relaxed text-text-variant">
            Simulate real users across chatbots, surveys, browsers, and agents — then review
            results under <span className="font-mono">jobs/</span>.
          </p>

          <button
            type="button"
            onClick={onOpenPersonaEval}
            className={`landing-cta-primary mt-8 ${FOCUS_RING}`}
          >
            PersonaEval cockpit
            <Sym name="arrow_forward" size={18} />
          </button>
        </div>
      </div>
    </StudioMeshShell>
  );
}

export default HomeView;
