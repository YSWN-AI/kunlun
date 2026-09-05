import{ad as Q,ab as n,an as V,ac as re,aU as De,ap as ft,aq as gt,b2 as mt,d as Fe,h as z,b3 as bt,b4 as pt,a2 as wt,b5 as yt,aB as _e,aW as _t,a7 as kt,ag as Ee,b6 as xt,al as St,r as v,am as zt,f as Ve,n as pe,b as Rt,a8 as Me,b7 as Ct,a9 as Tt,v as I,ai as ie,ar as de,aN as ce,b8 as Dt,R as N,I as Vt,D as Mt,o as _,c as M,a as r,u as m,p as ue,s as ve,j as P,k as B,K as J,x as Pe,t as T,F as we,l as ye,Q as Be,_ as Pt}from"./index-wHqlCVHi.js";import{I as Bt}from"./InlineNotice-D5mpStKv.js";import{a as Z,N as $t}from"./Tabs-Dy4rQU4p.js";import{N as $e}from"./Tag-CodsH--1.js";import{N as Ie}from"./Select-1IsvWhSe.js";import"./Add-8a0AOq2B.js";import"./Suffix-DzKYYMWH.js";import"./create-DyFs6GM1.js";import"./Empty-C1m5NISZ.js";const It=Q([n("slider",`
 display: block;
 padding: calc((var(--n-handle-size) - var(--n-rail-height)) / 2) 0;
 position: relative;
 z-index: 0;
 width: 100%;
 cursor: pointer;
 user-select: none;
 -webkit-user-select: none;
 `,[V("reverse",[n("slider-handles",[n("slider-handle-wrapper",`
 transform: translate(50%, -50%);
 `)]),n("slider-dots",[n("slider-dot",`
 transform: translateX(50%, -50%);
 `)]),V("vertical",[n("slider-handles",[n("slider-handle-wrapper",`
 transform: translate(-50%, -50%);
 `)]),n("slider-marks",[n("slider-mark",`
 transform: translateY(calc(-50% + var(--n-dot-height) / 2));
 `)]),n("slider-dots",[n("slider-dot",`
 transform: translateX(-50%) translateY(0);
 `)])])]),V("vertical",`
 box-sizing: content-box;
 padding: 0 calc((var(--n-handle-size) - var(--n-rail-height)) / 2);
 width: var(--n-rail-width-vertical);
 height: 100%;
 `,[n("slider-handles",`
 top: calc(var(--n-handle-size) / 2);
 right: 0;
 bottom: calc(var(--n-handle-size) / 2);
 left: 0;
 `,[n("slider-handle-wrapper",`
 top: unset;
 left: 50%;
 transform: translate(-50%, 50%);
 `)]),n("slider-rail",`
 height: 100%;
 `,[re("fill",`
 top: unset;
 right: 0;
 bottom: unset;
 left: 0;
 `)]),V("with-mark",`
 width: var(--n-rail-width-vertical);
 margin: 0 32px 0 8px;
 `),n("slider-marks",`
 top: calc(var(--n-handle-size) / 2);
 right: unset;
 bottom: calc(var(--n-handle-size) / 2);
 left: 22px;
 font-size: var(--n-mark-font-size);
 `,[n("slider-mark",`
 transform: translateY(50%);
 white-space: nowrap;
 `)]),n("slider-dots",`
 top: calc(var(--n-handle-size) / 2);
 right: unset;
 bottom: calc(var(--n-handle-size) / 2);
 left: 50%;
 `,[n("slider-dot",`
 transform: translateX(-50%) translateY(50%);
 `)])]),V("disabled",`
 cursor: not-allowed;
 opacity: var(--n-opacity-disabled);
 `,[n("slider-handle",`
 cursor: not-allowed;
 `)]),V("with-mark",`
 width: 100%;
 margin: 8px 0 32px 0;
 `),Q("&:hover",[n("slider-rail",{backgroundColor:"var(--n-rail-color-hover)"},[re("fill",{backgroundColor:"var(--n-fill-color-hover)"})]),n("slider-handle",{boxShadow:"var(--n-handle-box-shadow-hover)"})]),V("active",[n("slider-rail",{backgroundColor:"var(--n-rail-color-hover)"},[re("fill",{backgroundColor:"var(--n-fill-color-hover)"})]),n("slider-handle",{boxShadow:"var(--n-handle-box-shadow-hover)"})]),n("slider-marks",`
 position: absolute;
 top: 18px;
 left: calc(var(--n-handle-size) / 2);
 right: calc(var(--n-handle-size) / 2);
 `,[n("slider-mark",`
 position: absolute;
 transform: translateX(-50%);
 white-space: nowrap;
 `)]),n("slider-rail",`
 width: 100%;
 position: relative;
 height: var(--n-rail-height);
 background-color: var(--n-rail-color);
 transition: background-color .3s var(--n-bezier);
 border-radius: calc(var(--n-rail-height) / 2);
 `,[re("fill",`
 position: absolute;
 top: 0;
 bottom: 0;
 border-radius: calc(var(--n-rail-height) / 2);
 transition: background-color .3s var(--n-bezier);
 background-color: var(--n-fill-color);
 `)]),n("slider-handles",`
 position: absolute;
 top: 0;
 right: calc(var(--n-handle-size) / 2);
 bottom: 0;
 left: calc(var(--n-handle-size) / 2);
 `,[n("slider-handle-wrapper",`
 outline: none;
 position: absolute;
 top: 50%;
 transform: translate(-50%, -50%);
 cursor: pointer;
 display: flex;
 `,[n("slider-handle",`
 height: var(--n-handle-size);
 width: var(--n-handle-size);
 border-radius: 50%;
 overflow: hidden;
 transition: box-shadow .2s var(--n-bezier), background-color .3s var(--n-bezier);
 background-color: var(--n-handle-color);
 box-shadow: var(--n-handle-box-shadow);
 `,[Q("&:hover",`
 box-shadow: var(--n-handle-box-shadow-hover);
 `)]),Q("&:focus",[n("slider-handle",`
 box-shadow: var(--n-handle-box-shadow-focus);
 `,[Q("&:hover",`
 box-shadow: var(--n-handle-box-shadow-active);
 `)])])])]),n("slider-dots",`
 position: absolute;
 top: 50%;
 left: calc(var(--n-handle-size) / 2);
 right: calc(var(--n-handle-size) / 2);
 `,[V("transition-disabled",[n("slider-dot","transition: none;")]),n("slider-dot",`
 transition:
 border-color .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier),
 background-color .3s var(--n-bezier);
 position: absolute;
 transform: translate(-50%, -50%);
 height: var(--n-dot-height);
 width: var(--n-dot-width);
 border-radius: var(--n-dot-border-radius);
 overflow: hidden;
 box-sizing: border-box;
 border: var(--n-dot-border);
 background-color: var(--n-dot-color);
 `,[V("active","border: var(--n-dot-border-active);")])])]),n("slider-handle-indicator",`
 font-size: var(--n-font-size);
 padding: 6px 10px;
 border-radius: var(--n-indicator-border-radius);
 color: var(--n-indicator-text-color);
 background-color: var(--n-indicator-color);
 box-shadow: var(--n-indicator-box-shadow);
 `,[De()]),n("slider-handle-indicator",`
 font-size: var(--n-font-size);
 padding: 6px 10px;
 border-radius: var(--n-indicator-border-radius);
 color: var(--n-indicator-text-color);
 background-color: var(--n-indicator-color);
 box-shadow: var(--n-indicator-box-shadow);
 `,[V("top",`
 margin-bottom: 12px;
 `),V("right",`
 margin-left: 12px;
 `),V("bottom",`
 margin-top: 12px;
 `),V("left",`
 margin-right: 12px;
 `),De()]),ft(n("slider",[n("slider-dot","background-color: var(--n-dot-color-modal);")])),gt(n("slider",[n("slider-dot","background-color: var(--n-dot-color-popover);")]))]);function Ne(s){return window.TouchEvent&&s instanceof window.TouchEvent}function Ae(){const s=new Map,c=D=>k=>{s.set(D,k)};return mt(()=>{s.clear()}),[s,c]}const Nt=0,At=Object.assign(Object.assign({},Ee.props),{to:_e.propTo,defaultValue:{type:[Number,Array],default:0},marks:Object,disabled:{type:Boolean,default:void 0},formatTooltip:Function,keyboard:{type:Boolean,default:!0},min:{type:Number,default:0},max:{type:Number,default:100},step:{type:[Number,String],default:1},range:Boolean,value:[Number,Array],placement:String,showTooltip:{type:Boolean,default:void 0},tooltip:{type:Boolean,default:!0},vertical:Boolean,reverse:Boolean,"onUpdate:value":[Function,Array],onUpdateValue:[Function,Array],onDragstart:[Function],onDragend:[Function]}),Ft=Fe({name:"Slider",props:At,slots:Object,setup(s){const{mergedClsPrefixRef:c,namespaceRef:D,inlineThemeDisabled:k}=kt(s),h=Ee("Slider","-slider",It,xt,s,c),f=v(null),[R,b]=Ae(),[j,L]=Ae(),X=v(new Set),F=St(s),{mergedDisabledRef:E}=F,Y=I(()=>{const{step:e}=s;if(Number(e)<=0||e==="mark")return 0;const t=e.toString();let a=0;return t.includes(".")&&(a=t.length-t.indexOf(".")-1),a}),A=v(s.defaultValue),i=Tt(s,"value"),g=zt(i,A),p=I(()=>{const{value:e}=g;return(s.range?e:[e]).map(ze)}),U=I(()=>p.value.length>2),q=I(()=>s.placement===void 0?s.vertical?"right":"top":s.placement),w=I(()=>{const{marks:e}=s;return e?Object.keys(e).map(Number.parseFloat):null}),o=v(-1),d=v(-1),C=v(-1),O=v(!1),ee=v(!1),he=I(()=>{const{vertical:e,reverse:t}=s;return e?t?"top":"bottom":t?"right":"left"}),Ue=I(()=>{if(U.value)return;const e=p.value,t=te(s.range?Math.min(...e):s.min),a=te(s.range?Math.max(...e):e[0]),{value:l}=he;return s.vertical?{[l]:`${t}%`,height:`${a-t}%`}:{[l]:`${t}%`,width:`${a-t}%`}}),He=I(()=>{const e=[],{marks:t}=s;if(t){const a=p.value.slice();a.sort((S,x)=>S-x);const{value:l}=he,{value:u}=U,{range:y}=s,$=u?()=>!1:S=>y?S>=a[0]&&S<=a[a.length-1]:S<=a[0];for(const S of Object.keys(t)){const x=Number(S);e.push({active:$(x),key:x,label:t[S],style:{[l]:`${te(x)}%`}})}}return e});function je(e,t){const a=te(e),{value:l}=he;return{[l]:`${a}%`,zIndex:t===o.value?1:0}}function ke(e){return s.showTooltip||C.value===e||o.value===e&&O.value}function Le(e){return O.value?!(o.value===e&&d.value===e):!0}function Oe(e){var t;~e&&(o.value=e,(t=R.get(e))===null||t===void 0||t.focus())}function Ke(){j.forEach((e,t)=>{ke(t)&&e.syncPosition()})}function xe(e){const{"onUpdate:value":t,onUpdateValue:a}=s,{nTriggerFormInput:l,nTriggerFormChange:u}=F;a&&ie(a,e),t&&ie(t,e),A.value=e,l(),u()}function Se(e){const{range:t}=s;if(t){if(Array.isArray(e)){const{value:a}=p;e.join()!==a.join()&&xe(e)}}else Array.isArray(e)||p.value[0]!==e&&xe(e)}function fe(e,t){if(s.range){const a=p.value.slice();a.splice(t,1,e),Se(a)}else Se(e)}function ge(e,t,a){const l=a!==void 0;a||(a=e-t>0?1:-1);const u=w.value||[],{step:y}=s;if(y==="mark"){const x=ae(e,u.concat(t),l?a:void 0);return x?x.value:t}if(y<=0)return t;const{value:$}=Y;let S;if(l){const x=Number((t/y).toFixed($)),H=Math.floor(x),me=x>H?H:H-1,be=x<H?H:H+1;S=ae(t,[Number((me*y).toFixed($)),Number((be*y).toFixed($)),...u],a)}else{const x=Ye(e);S=ae(e,[...u,x])}return S?ze(S.value):t}function ze(e){return Math.min(s.max,Math.max(s.min,e))}function te(e){const{max:t,min:a}=s;return(e-a)/(t-a)*100}function Xe(e){const{max:t,min:a}=s;return a+(t-a)*e}function Ye(e){const{step:t,min:a}=s;if(Number(t)<=0||t==="mark")return e;const l=Math.round((e-a)/t)*t+a;return Number(l.toFixed(Y.value))}function ae(e,t=w.value,a){if(!t?.length)return null;let l=null,u=-1;for(;++u<t.length;){const y=t[u]-e,$=Math.abs(y);(a===void 0||y*a>0)&&(l===null||$<l.distance)&&(l={index:u,distance:$,value:t[u]})}return l}function Re(e){const t=f.value;if(!t)return;const a=Ne(e)?e.touches[0]:e,l=t.getBoundingClientRect();let u;return s.vertical?u=(l.bottom-a.clientY)/l.height:u=(a.clientX-l.left)/l.width,s.reverse&&(u=1-u),Xe(u)}function We(e){if(E.value||!s.keyboard)return;const{vertical:t,reverse:a}=s;switch(e.key){case"ArrowUp":e.preventDefault(),se(t&&a?-1:1);break;case"ArrowRight":e.preventDefault(),se(!t&&a?-1:1);break;case"ArrowDown":e.preventDefault(),se(t&&a?1:-1);break;case"ArrowLeft":e.preventDefault(),se(!t&&a?1:-1);break}}function se(e){const t=o.value;if(t===-1)return;const{step:a}=s,l=p.value[t],u=Number(a)<=0||a==="mark"?l:l+a*e;fe(ge(u,l,e>0?1:-1),t)}function Ge(e){var t,a;if(E.value||!Ne(e)&&e.button!==Nt)return;const l=Re(e);if(l===void 0)return;const u=p.value.slice(),y=s.range?(a=(t=ae(l,u))===null||t===void 0?void 0:t.index)!==null&&a!==void 0?a:-1:0;y!==-1&&(e.preventDefault(),Oe(y),qe(),fe(ge(l,p.value[y]),y))}function qe(){O.value||(O.value=!0,s.onDragstart&&ie(s.onDragstart),de("touchend",document,le),de("mouseup",document,le),de("touchmove",document,ne),de("mousemove",document,ne))}function oe(){O.value&&(O.value=!1,s.onDragend&&ie(s.onDragend),ce("touchend",document,le),ce("mouseup",document,le),ce("touchmove",document,ne),ce("mousemove",document,ne))}function ne(e){const{value:t}=o;if(!O.value||t===-1){oe();return}const a=Re(e);a!==void 0&&fe(ge(a,p.value[t]),t)}function le(){oe()}function Qe(e){o.value=e,E.value||(C.value=e)}function Je(e){o.value===e&&(o.value=-1,oe()),C.value===e&&(C.value=-1)}function Ze(e){C.value=e}function et(e){C.value===e&&(C.value=-1)}Ve(o,(e,t)=>void pe(()=>d.value=t)),Ve(g,()=>{if(s.marks){if(ee.value)return;ee.value=!0,pe(()=>{ee.value=!1})}pe(Ke)}),Rt(()=>{oe()});const Ce=I(()=>{const{self:{markFontSize:e,railColor:t,railColorHover:a,fillColor:l,fillColorHover:u,handleColor:y,opacityDisabled:$,dotColor:S,dotColorModal:x,handleBoxShadow:H,handleBoxShadowHover:me,handleBoxShadowActive:be,handleBoxShadowFocus:tt,dotBorder:at,dotBoxShadow:st,railHeight:ot,railWidthVertical:nt,handleSize:lt,dotHeight:rt,dotWidth:it,dotBorderRadius:dt,fontSize:ct,dotBorderActive:ut,dotColorPopover:vt},common:{cubicBezierEaseInOut:ht}}=h.value;return{"--n-bezier":ht,"--n-dot-border":at,"--n-dot-border-active":ut,"--n-dot-border-radius":dt,"--n-dot-box-shadow":st,"--n-dot-color":S,"--n-dot-color-modal":x,"--n-dot-color-popover":vt,"--n-dot-height":rt,"--n-dot-width":it,"--n-fill-color":l,"--n-fill-color-hover":u,"--n-font-size":ct,"--n-handle-box-shadow":H,"--n-handle-box-shadow-active":be,"--n-handle-box-shadow-focus":tt,"--n-handle-box-shadow-hover":me,"--n-handle-color":y,"--n-handle-size":lt,"--n-opacity-disabled":$,"--n-rail-color":t,"--n-rail-color-hover":a,"--n-rail-height":ot,"--n-rail-width-vertical":nt,"--n-mark-font-size":e}}),W=k?Me("slider",void 0,Ce,s):void 0,Te=I(()=>{const{self:{fontSize:e,indicatorColor:t,indicatorBoxShadow:a,indicatorTextColor:l,indicatorBorderRadius:u}}=h.value;return{"--n-font-size":e,"--n-indicator-border-radius":u,"--n-indicator-box-shadow":a,"--n-indicator-color":t,"--n-indicator-text-color":l}}),G=k?Me("slider-indicator",void 0,Te,s):void 0;return{mergedClsPrefix:c,namespace:D,uncontrolledValue:A,mergedValue:g,mergedDisabled:E,mergedPlacement:q,isMounted:Ct(),adjustedTo:_e(s),dotTransitionDisabled:ee,markInfos:He,isShowTooltip:ke,shouldKeepTooltipTransition:Le,handleRailRef:f,setHandleRefs:b,setFollowerRefs:L,fillStyle:Ue,getHandleStyle:je,activeIndex:o,arrifiedValues:p,followerEnabledIndexSet:X,handleRailMouseDown:Ge,handleHandleFocus:Qe,handleHandleBlur:Je,handleHandleMouseEnter:Ze,handleHandleMouseLeave:et,handleRailKeyDown:We,indicatorCssVars:k?void 0:Te,indicatorThemeClass:G?.themeClass,indicatorOnRender:G?.onRender,cssVars:k?void 0:Ce,themeClass:W?.themeClass,onRender:W?.onRender}},render(){var s;const{mergedClsPrefix:c,themeClass:D,formatTooltip:k}=this;return(s=this.onRender)===null||s===void 0||s.call(this),z("div",{class:[`${c}-slider`,D,{[`${c}-slider--disabled`]:this.mergedDisabled,[`${c}-slider--active`]:this.activeIndex!==-1,[`${c}-slider--with-mark`]:this.marks,[`${c}-slider--vertical`]:this.vertical,[`${c}-slider--reverse`]:this.reverse}],style:this.cssVars,onKeydown:this.handleRailKeyDown,onMousedown:this.handleRailMouseDown,onTouchstart:this.handleRailMouseDown},z("div",{class:`${c}-slider-rail`},z("div",{class:`${c}-slider-rail__fill`,style:this.fillStyle}),this.marks?z("div",{class:[`${c}-slider-dots`,this.dotTransitionDisabled&&`${c}-slider-dots--transition-disabled`]},this.markInfos.map(h=>z("div",{key:h.key,class:[`${c}-slider-dot`,{[`${c}-slider-dot--active`]:h.active}],style:h.style}))):null,z("div",{ref:"handleRailRef",class:`${c}-slider-handles`},this.arrifiedValues.map((h,f)=>{const R=this.isShowTooltip(f);return z(bt,null,{default:()=>[z(pt,null,{default:()=>z("div",{ref:this.setHandleRefs(f),class:`${c}-slider-handle-wrapper`,tabindex:this.mergedDisabled?-1:0,role:"slider","aria-valuenow":h,"aria-valuemin":this.min,"aria-valuemax":this.max,"aria-orientation":this.vertical?"vertical":"horizontal","aria-disabled":this.disabled,style:this.getHandleStyle(h,f),onFocus:()=>{this.handleHandleFocus(f)},onBlur:()=>{this.handleHandleBlur(f)},onMouseenter:()=>{this.handleHandleMouseEnter(f)},onMouseleave:()=>{this.handleHandleMouseLeave(f)}},wt(this.$slots.thumb,()=>[z("div",{class:`${c}-slider-handle`})]))}),this.tooltip&&z(yt,{ref:this.setFollowerRefs(f),show:R,to:this.adjustedTo,enabled:this.showTooltip&&!this.range||this.followerEnabledIndexSet.has(f),teleportDisabled:this.adjustedTo===_e.tdkey,placement:this.mergedPlacement,containerClass:this.namespace},{default:()=>z(_t,{name:"fade-in-scale-up-transition",appear:this.isMounted,css:this.shouldKeepTooltipTransition(f),onEnter:()=>{this.followerEnabledIndexSet.add(f)},onAfterLeave:()=>{this.followerEnabledIndexSet.delete(f)}},{default:()=>{var b;return R?((b=this.indicatorOnRender)===null||b===void 0||b.call(this),z("div",{class:[`${c}-slider-handle-indicator`,this.indicatorThemeClass,`${c}-slider-handle-indicator--${this.mergedPlacement}`],style:this.indicatorCssVars},typeof k=="function"?k(h):h)):null}})})]})})),this.marks?z("div",{class:`${c}-slider-marks`},this.markInfos.map(h=>z("div",{key:h.key,class:`${c}-slider-mark`,style:h.style},typeof h.label=="function"?h.label():h.label))):null))}});function K(s){return s instanceof Error?s.message:String(s)}const Et=Dt("config",()=>{const s=v([]),c=v([]),D=v({}),k=v(null),h=v([]),f=v([]),R=v(!1),b=v("");async function j(){try{const i=await N.getParamDefs();s.value=i.params||[],c.value=i.agents||[]}catch(i){b.value=K(i)}}async function L(i="default"){try{const g=await N.getAllParams(i);D.value=g.params||{}}catch(g){b.value=K(g)}}async function X(i,g,p,U){try{await N.setParam(i,g,p,U),D.value[U]&&(D.value[U][g]=p)}catch(q){b.value=K(q)}}async function F(i){R.value=!0;try{const g=await N.getBookConfig(i);k.value=g.config||null}catch(g){b.value=K(g)}finally{R.value=!1}}async function E(i,g){try{return await N.updateBookConfig(i,g),await F(i),!0}catch(p){return b.value=K(p),!1}}async function Y(){try{const i=await N.listGenres();h.value=i.genres||[]}catch(i){b.value=K(i)}}async function A(i){try{const g=await N.listPrompts(i);f.value=g.prompts||[]}catch(g){b.value=K(g)}}return{paramDefs:s,agents:c,allParams:D,bookConfig:k,genres:h,prompts:f,loading:R,error:b,loadParamDefs:j,loadAllParams:L,setParam:X,loadBookConfig:F,saveBookConfig:E,loadGenres:Y,loadPrompts:A}}),Ut={class:"settings-view"},Ht={class:"settings-group"},jt={class:"settings-row"},Lt={key:0,class:"settings-loading"},Ot={key:0,class:"settings-empty"},Kt={class:"settings-row__header"},Xt={class:"settings-row__label"},Yt={class:"settings-row__desc"},Wt={class:"settings-row__control"},Gt={class:"settings-row__number"},qt={key:0,class:"settings-loading"},Qt={key:0,class:"settings-empty"},Jt={class:"settings-row__label"},Zt={class:"settings-row__value"},ea={class:"settings-group"},ta={class:"settings-row"},aa={class:"settings-row"},sa={key:0,class:"settings-loading"},oa={class:"usage-stats"},na={class:"usage-stat"},la={class:"usage-stat__value"},ra={class:"usage-stat"},ia={class:"usage-stat__value"},da={class:"usage-stat"},ca={class:"usage-stat__value"},ua={key:0,class:"usage-by-agent"},va={class:"settings-row__label"},ha={class:"settings-row__value"},fa=Fe({__name:"SettingsView",setup(s){const c=Vt(),D=Et(),k=c.backendConnected,h=v("general"),f=v([]),R=Be({}),b=v(!1),j=v([]),L=v(!1),X=v("txt"),F=v("all"),E=[{label:"纯文本 (.txt)",value:"txt"},{label:"EPUB",value:"epub"},{label:"Markdown",value:"md"}],Y=[{label:"全书",value:"all"},{label:"指定章节",value:"chapters"}],A=v(!1),i=Be({totalTokens:0,totalCost:0,calls:0,byAgent:null});async function g(){b.value=!0;try{await D.loadParamDefs(),f.value=D.paramDefs||[];for(const w of f.value)w.key in R||(R[w.key]=w.default)}catch{}finally{b.value=!1}}async function p(){L.value=!0;try{const w=await N.listPrompts("default");j.value=w.prompts||[]}catch{}finally{L.value=!1}}async function U(){A.value=!0;try{const w=await N.getUsage();i.totalTokens=w.total_tokens||0,i.totalCost=w.total_cost_usd||0,i.calls=w.calls||0,i.byAgent=w.by_agent||null}catch{}finally{A.value=!1}}async function q(w,o){R[w]=o;try{await N.setParam("default",w,o,"default"),c.showToast("参数已更新","success")}catch(d){c.showToast(`参数更新失败: ${d.message}`,"error")}}return Mt(()=>{g(),p(),U()}),(w,o)=>(_(),M("div",Ut,[o[12]||(o[12]=r("div",{class:"settings-view__header"},[r("h2",{class:"settings-view__title"},"设置")],-1)),m(k)?ve("",!0):(_(),ue(Bt,{key:0,type:"warning",message:"后端服务未连接，部分数据不可用"})),P(m($t),{value:h.value,"onUpdate:value":o[2]||(o[2]=d=>h.value=d),type:"line",animated:""},{default:B(()=>[P(m(Z),{name:"general",tab:"通用"},{default:B(()=>[P(m(J),{bordered:!0,title:"基本设置",size:"small",class:"settings-card"},{default:B(()=>[r("div",Ht,[o[4]||(o[4]=r("div",{class:"settings-row"},[r("span",{class:"settings-row__label"},"后端地址"),r("span",{class:"settings-row__value"},"http://127.0.0.1:8000")],-1)),r("div",jt,[o[3]||(o[3]=r("span",{class:"settings-row__label"},"连接状态",-1)),P(m($e),{type:m(k)?"success":"error",size:"small",bordered:!1},{default:B(()=>[Pe(T(m(k)?"已连接":"未连接"),1)]),_:1},8,["type"])]),o[5]||(o[5]=r("div",{class:"settings-row"},[r("span",{class:"settings-row__label"},"版本"),r("span",{class:"settings-row__value"},"v0.2.0")],-1))])]),_:1})]),_:1}),P(m(Z),{name:"params",tab:"模型参数"},{default:B(()=>[b.value?(_(),M("div",Lt,"加载中...")):(_(),ue(m(J),{key:1,bordered:!0,title:"AI 模型参数",size:"small",class:"settings-card"},{default:B(()=>[f.value.length===0?(_(),M("div",Ot," 暂无参数定义 ")):ve("",!0),(_(!0),M(we,null,ye(f.value,d=>(_(),M("div",{key:d.key,class:"settings-row"},[r("div",Kt,[r("span",Xt,T(d.label),1),r("span",Yt,T(d.description),1)]),r("div",Wt,[P(m(Ft),{value:R[d.key]??d.default,min:d.min,max:d.max,step:d.step,"format-tooltip":C=>C.toFixed(2),"onUpdate:value":C=>q(d.key,C)},null,8,["value","min","max","step","format-tooltip","onUpdate:value"]),r("span",Gt,T((R[d.key]??d.default).toFixed(2)),1)])]))),128))]),_:1}))]),_:1}),P(m(Z),{name:"prompts",tab:"Prompt"},{default:B(()=>[L.value?(_(),M("div",qt,"加载中...")):(_(),ue(m(J),{key:1,bordered:!0,title:"Prompt 管理",size:"small",class:"settings-card"},{default:B(()=>[j.value.length===0?(_(),M("div",Qt," 暂无 Prompt 配置 ")):ve("",!0),(_(!0),M(we,null,ye(j.value,d=>(_(),M("div",{key:d.agent,class:"settings-row"},[r("span",Jt,T(d.agent),1),P(m($e),{type:d.has_override?"warning":"default",size:"small",bordered:!1},{default:B(()=>[Pe(T(d.has_override?"已自定义":"默认"),1)]),_:2},1032,["type"]),r("span",Zt,T(d.length)+" 字符",1)]))),128))]),_:1}))]),_:1}),P(m(Z),{name:"export",tab:"导出"},{default:B(()=>[P(m(J),{bordered:!0,title:"导出选项",size:"small",class:"settings-card"},{default:B(()=>[r("div",ea,[r("div",ta,[o[6]||(o[6]=r("span",{class:"settings-row__label"},"默认格式",-1)),P(m(Ie),{value:X.value,"onUpdate:value":o[0]||(o[0]=d=>X.value=d),options:E,size:"small",style:{width:"140px"}},null,8,["value"])]),r("div",aa,[o[7]||(o[7]=r("span",{class:"settings-row__label"},"默认范围",-1)),P(m(Ie),{value:F.value,"onUpdate:value":o[1]||(o[1]=d=>F.value=d),options:Y,size:"small",style:{width:"140px"}},null,8,["value"])])])]),_:1})]),_:1}),P(m(Z),{name:"usage",tab:"用量统计"},{default:B(()=>[A.value?(_(),M("div",sa,"加载中...")):(_(),ue(m(J),{key:1,bordered:!0,title:"API 用量",size:"small",class:"settings-card"},{default:B(()=>[r("div",oa,[r("div",na,[r("span",la,T((i.totalTokens||0).toLocaleString()),1),o[8]||(o[8]=r("span",{class:"usage-stat__label"},"总 Token",-1))]),r("div",ra,[r("span",ia,"$"+T((i.totalCost||0).toFixed(4)),1),o[9]||(o[9]=r("span",{class:"usage-stat__label"},"总成本",-1))]),r("div",da,[r("span",ca,T((i.calls||0).toLocaleString()),1),o[10]||(o[10]=r("span",{class:"usage-stat__label"},"调用次数",-1))])]),i.byAgent&&Object.keys(i.byAgent).length?(_(),M("div",ua,[o[11]||(o[11]=r("h4",{class:"usage-by-agent__title"},"按 Agent 细分",-1)),(_(!0),M(we,null,ye(i.byAgent,(d,C)=>(_(),M("div",{key:C,class:"settings-row"},[r("span",va,T(C),1),r("span",ha,T((d.total_tokens||0).toLocaleString())+" Token / $"+T((d.total_cost||0).toFixed(4))+" / "+T((d.calls||0).toLocaleString())+" 调用 ",1)]))),128))])):ve("",!0)]),_:1}))]),_:1})]),_:1},8,["value"])]))}}),Sa=Pt(fa,[["__scopeId","data-v-04895532"]]);export{Sa as default};
