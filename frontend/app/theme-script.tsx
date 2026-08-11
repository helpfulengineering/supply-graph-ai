/**
 * Resolve the world and mode before first paint.
 *
 * Without this the document paints with the default palette and then flips
 * once React mounts — the flash of wrong theme. It runs as a blocking inline
 * script in <head> for that reason: it must finish before the first frame, so
 * it is deliberately tiny and touches nothing but documentElement.
 *
 * Mirrors the resolution order in hooks/useDarkMode.ts. If the two ever
 * disagree the page flickers, so change them together.
 */
const SCRIPT = `(function(){try{
var t=localStorage.getItem("ohm-theme");
var m=localStorage.getItem("ohm-color-scheme");
var d=document.documentElement;
d.setAttribute("data-ttm-theme",t||"ttm");
if(m===null){m=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";}
if(m==="dark"){d.classList.add("dark");}
}catch(e){}})();`;

export function ThemeScript() {
  return <script dangerouslySetInnerHTML={{ __html: SCRIPT }} />;
}
