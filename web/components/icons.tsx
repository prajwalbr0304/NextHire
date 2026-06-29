type P = { className?: string };
const S = ({ className, children }: P & { children: React.ReactNode }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{children}</svg>
);

export const IconGrid = (p: P) => (<S {...p}><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></S>);
export const IconChart = (p: P) => (<S {...p}><path d="M3 3v18h18"/><path d="M7 15l3-4 3 3 4-7"/></S>);
export const IconShield = (p: P) => (<S {...p}><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z"/><path d="M9 12l2 2 4-4"/></S>);
export const IconAlert = (p: P) => (<S {...p}><path d="M12 3l9 16H3l9-16z"/><path d="M12 10v4"/><circle cx="12" cy="17" r=".6" fill="currentColor"/></S>);
export const IconTarget = (p: P) => (<S {...p}><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r=".8" fill="currentColor"/></S>);
export const IconSettings = (p: P) => (<S {...p}><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.5-2.4 1a7 7 0 0 0-1.7-1l-.3-2.5h-4l-.3 2.5a7 7 0 0 0-1.7 1l-2.4-1-2 3.5L4.1 11a7 7 0 0 0 0 2l-2 1.5 2 3.5 2.4-1a7 7 0 0 0 1.7 1l.3 2.5h4l.3-2.5a7 7 0 0 0 1.7-1l2.4 1 2-3.5-2-1.5a7 7 0 0 0 .1-1z"/></S>);
export const IconSearch = (p: P) => (<S {...p}><circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/></S>);
export const IconUpload = (p: P) => (<S {...p}><path d="M12 16V4"/><path d="M7 9l5-5 5 5"/><path d="M4 20h16"/></S>);
export const IconDownload = (p: P) => (<S {...p}><path d="M12 4v12"/><path d="M7 11l5 5 5-5"/><path d="M4 20h16"/></S>);
export const IconRefresh = (p: P) => (<S {...p}><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/></S>);
export const IconSpark = (p: P) => (<S {...p}><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z"/></S>);
export const IconCheck = (p: P) => (<S {...p}><path d="M20 6L9 17l-5-5"/></S>);
export const IconChevron = (p: P) => (<S {...p}><path d="M9 6l6 6-6 6"/></S>);
export const IconClose = (p: P) => (<S {...p}><path d="M6 6l12 12M18 6L6 18"/></S>);
export const IconClock = (p: P) => (<S {...p}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></S>);
export const IconUsers = (p: P) => (<S {...p}><circle cx="9" cy="8" r="3.2"/><path d="M3 20a6 6 0 0 1 12 0"/><path d="M16 5.5a3 3 0 0 1 0 5.6"/><path d="M21 20a5.5 5.5 0 0 0-4-5.3"/></S>);
export const IconBolt = (p: P) => (<S {...p}><path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/></S>);
export const IconBriefcase = (p: P) => (<S {...p}><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></S>);
export const IconTerminal = (p: P) => (<S {...p}><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3"/><path d="M13 15h4"/></S>);
export const IconFile = (p: P) => (<S {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z"/><path d="M14 3v5h5"/></S>);
export const IconWrench = (p: P) => (<S {...p}><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></S>);
export const IconDots = (p: P) => (<S {...p}><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></S>);
export const IconPlus = (p: P) => (<S {...p}><path d="M12 5v14M5 12h14"/></S>);
export const IconTrash = (p: P) => (<S {...p}><path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M10 11v6M14 11v6"/></S>);
export const IconSend = (p: P) => (<S {...p}><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></S>);
export const IconDatabase = (p: P) => (<S {...p}><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/></S>);
export const IconLayers = (p: P) => (<S {...p}><path d="M12 2l9 5-9 5-9-5 9-5z"/><path d="M3 12l9 5 9-5"/><path d="M3 17l9 5 9-5"/></S>);
export const IconEye = (p: P) => (<S {...p}><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></S>);
export const IconCompare = (p: P) => (<S {...p}><rect x="2" y="8" width="8" height="13" rx="1"/><rect x="14" y="8" width="8" height="13" rx="1"/><path d="M10 8V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3"/><path d="M10 16v3a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1v-3"/><path d="M14 16v3a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-3"/></S>);
export const IconBalance = (p: P) => (<S {...p}><path d="M12 3v18"/><path d="M7 21h10"/><path d="M5 7h14"/><path d="M8 4l-3 3"/><path d="M16 4l3 3"/><path d="M5 7l-3 6a3 3 0 0 0 6 0l-3-6z"/><path d="M19 7l-3 6a3 3 0 0 0 6 0l-3-6z"/></S>);
export const IconFilter = (p: P) => (<S {...p}><path d="M3 5h18l-7 8v6l-4-2v-4L3 5z"/></S>);
export const IconMenu = (p: P) => (<S {...p}><path d="M3 6h18M3 12h18M3 18h18"/></S>);
export const IconCopy = (p: P) => (<S {...p}><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></S>);
export const IconPencil = (p: P) => (<S {...p}><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/></S>);
export const IconStar = ({ className, filled }: P & { filled?: boolean }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" fill={filled ? "currentColor" : "none"}/>
  </svg>
);

// Multi-color donut icon for Adjust Weights
export const IconDonut = (p: P) => (
  <svg className={p.className} viewBox="0 0 24 24" fill="none">
    {/* Outer ring segments with different colors */}
    <circle cx="12" cy="12" r="10" stroke="#10A37F" strokeWidth="2.5" strokeDasharray="12 52" strokeDashoffset="0" strokeLinecap="round" transform="rotate(-90 12 12)" />
    <circle cx="12" cy="12" r="10" stroke="#f59e0b" strokeWidth="2.5" strokeDasharray="10 52" strokeDashoffset="-12" strokeLinecap="round" transform="rotate(-90 12 12)" />
    <circle cx="12" cy="12" r="10" stroke="#10b981" strokeWidth="2.5" strokeDasharray="14 52" strokeDashoffset="-22" strokeLinecap="round" transform="rotate(-90 12 12)" />
    <circle cx="12" cy="12" r="10" stroke="#ec4899" strokeWidth="2.5" strokeDasharray="8 52" strokeDashoffset="-36" strokeLinecap="round" transform="rotate(-90 12 12)" />
    <circle cx="12" cy="12" r="10" stroke="#06b6d4" strokeWidth="2.5" strokeDasharray="10 52" strokeDashoffset="-44" strokeLinecap="round" transform="rotate(-90 12 12)" />
    <circle cx="12" cy="12" r="10" stroke="#3b82f6" strokeWidth="2.5" strokeDasharray="10 52" strokeDashoffset="-54" strokeLinecap="round" transform="rotate(-90 12 12)" />
    {/* Center circle for donut hole effect */}
    <circle cx="12" cy="12" r="4" fill="white" />
  </svg>
);
