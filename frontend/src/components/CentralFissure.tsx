import React from 'react'

export const CentralFissure: React.FC = () => {
  return (
    <div
      aria-hidden="true"
      className="hidden lg:flex flex-col items-center justify-center relative w-12 my-auto select-none pointer-events-none opacity-80"
    >
      {/* Central fissure ambient glow */}
      <div className="absolute inset-y-0 w-2 bg-gradient-to-b from-transparent via-crimson-600/30 to-transparent blur-md" />

      {/* SVG Tectonic Chasm Path */}
      <svg
        className="w-10 h-[650px] text-void-700/80 filter drop-shadow-[0_0_8px_rgba(220,38,38,0.25)]"
        viewBox="0 0 40 650"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M20 0 
             L16 45 L24 85 L14 140 L26 195 L17 250 L25 310 
             L15 375 L27 430 L16 490 L24 550 L18 600 L20 650"
          stroke="rgba(232, 230, 223, 0.15)"
          strokeWidth="1.5"
          strokeDasharray="4 2"
        />
        <path
          d="M20 10 
             L25 50 L18 95 L27 150 L15 205 L26 260 L18 320 
             L28 385 L17 440 L25 500 L19 560 L22 610 L20 650"
          stroke="rgba(220, 38, 38, 0.45)"
          strokeWidth="1"
        />
        {/* Subtle cross marker nodes along the fault line */}
        <text x="14" y="145" fill="rgba(232, 230, 223, 0.3)" fontSize="10" fontFamily="monospace">
          +
        </text>
        <text x="14" y="325" fill="rgba(220, 38, 38, 0.6)" fontSize="10" fontFamily="monospace">
          +
        </text>
        <text x="14" y="505" fill="rgba(232, 230, 223, 0.3)" fontSize="10" fontFamily="monospace">
          +
        </text>
      </svg>
    </div>
  )
}
