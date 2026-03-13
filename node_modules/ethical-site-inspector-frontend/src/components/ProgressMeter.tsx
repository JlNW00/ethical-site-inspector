interface ProgressMeterProps {
  value: number;
}

export function ProgressMeter({ value }: ProgressMeterProps) {
  return (
    <div className="meter-track" aria-label="Audit progress">
      <div className="meter-bar" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}
