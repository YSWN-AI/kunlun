import{ab as le,an as l,ac as b,az as x,ad as z,d as te,a3 as _,h as v,bh as se,a7 as ie,ag as T,ce as de,av as he,a8 as ge,v as B,cf as I,r as be,ai as ve,ax as c,bl as ue,ak as ke,a9 as Ce,a1 as fe}from"./index-wHqlCVHi.js";const pe={color:Object,type:{type:String,default:"default"},round:Boolean,size:String,closable:Boolean,disabled:{type:Boolean,default:void 0}},me=le("tag",`
 --n-close-margin: var(--n-close-margin-top) var(--n-close-margin-right) var(--n-close-margin-bottom) var(--n-close-margin-left);
 white-space: nowrap;
 position: relative;
 box-sizing: border-box;
 cursor: default;
 display: inline-flex;
 align-items: center;
 flex-wrap: nowrap;
 padding: var(--n-padding);
 border-radius: var(--n-border-radius);
 color: var(--n-text-color);
 background-color: var(--n-color);
 transition: 
 border-color .3s var(--n-bezier),
 background-color .3s var(--n-bezier),
 color .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier),
 opacity .3s var(--n-bezier);
 line-height: 1;
 height: var(--n-height);
 font-size: var(--n-font-size);
`,[l("strong",`
 font-weight: var(--n-font-weight-strong);
 `),b("border",`
 pointer-events: none;
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 border-radius: inherit;
 border: var(--n-border);
 transition: border-color .3s var(--n-bezier);
 `),b("icon",`
 display: flex;
 margin: 0 4px 0 0;
 color: var(--n-text-color);
 transition: color .3s var(--n-bezier);
 font-size: var(--n-avatar-size-override);
 `),b("avatar",`
 display: flex;
 margin: 0 6px 0 0;
 `),b("close",`
 margin: var(--n-close-margin);
 transition:
 background-color .3s var(--n-bezier),
 color .3s var(--n-bezier);
 `),l("round",`
 padding: 0 calc(var(--n-height) / 3);
 border-radius: calc(var(--n-height) / 2);
 `,[b("icon",`
 margin: 0 4px 0 calc((var(--n-height) - 8px) / -2);
 `),b("avatar",`
 margin: 0 6px 0 calc((var(--n-height) - 8px) / -2);
 `),l("closable",`
 padding: 0 calc(var(--n-height) / 4) 0 calc(var(--n-height) / 3);
 `)]),l("icon, avatar",[l("round",`
 padding: 0 calc(var(--n-height) / 3) 0 calc(var(--n-height) / 2);
 `)]),l("disabled",`
 cursor: not-allowed !important;
 opacity: var(--n-opacity-disabled);
 `),l("checkable",`
 cursor: pointer;
 box-shadow: none;
 color: var(--n-text-color-checkable);
 background-color: var(--n-color-checkable);
 `,[x("disabled",[z("&:hover","background-color: var(--n-color-hover-checkable);",[x("checked","color: var(--n-text-color-hover-checkable);")]),z("&:active","background-color: var(--n-color-pressed-checkable);",[x("checked","color: var(--n-text-color-pressed-checkable);")])]),l("checked",`
 color: var(--n-text-color-checked);
 background-color: var(--n-color-checked);
 `,[x("disabled",[z("&:hover","background-color: var(--n-color-checked-hover);"),z("&:active","background-color: var(--n-color-checked-pressed);")])])])]),xe=Object.assign(Object.assign(Object.assign({},T.props),pe),{bordered:{type:Boolean,default:void 0},checked:Boolean,checkable:Boolean,strong:Boolean,triggerClickOnClose:Boolean,onClose:[Array,Function],onMouseenter:Function,onMouseleave:Function,"onUpdate:checked":Function,onUpdateChecked:Function,internalCloseFocusable:{type:Boolean,default:!0},internalCloseIsButtonTag:{type:Boolean,default:!0},onCheckedChange:Function}),ze=fe("n-tag"),Be=te({name:"Tag",props:xe,slots:Object,setup(r){const i=be(null),{mergedBorderedRef:o,mergedClsPrefixRef:u,inlineThemeDisabled:k,mergedRtlRef:y,mergedComponentPropsRef:d}=ie(r),h=B(()=>{var e,a;return r.size||((a=(e=d?.value)===null||e===void 0?void 0:e.Tag)===null||a===void 0?void 0:a.size)||"medium"}),C=T("Tag","-tag",me,de,r,u);ke(ze,{roundRef:Ce(r,"round")});function f(){if(!r.disabled&&r.checkable){const{checked:e,onCheckedChange:a,onUpdateChecked:s,"onUpdate:checked":n}=r;s&&s(!e),n&&n(!e),a&&a(!e)}}function p(e){if(r.triggerClickOnClose||e.stopPropagation(),!r.disabled){const{onClose:a}=r;a&&ve(a,e)}}const t={setTextContent(e){const{value:a}=i;a&&(a.textContent=e)}},M=he("Tag",y,u),$=B(()=>{const{type:e,color:{color:a,textColor:s}={}}=r,n=h.value,{common:{cubicBezierEaseInOut:S},self:{padding:w,closeMargin:O,borderRadius:j,opacityDisabled:F,textColorCheckable:H,textColorHoverCheckable:N,textColorPressedCheckable:E,textColorChecked:U,colorCheckable:D,colorHoverCheckable:K,colorPressedCheckable:V,colorChecked:W,colorCheckedHover:A,colorCheckedPressed:L,closeBorderRadius:q,fontWeightStrong:G,[c("colorBordered",e)]:J,[c("closeSize",n)]:Q,[c("closeIconSize",n)]:X,[c("fontSize",n)]:Y,[c("height",n)]:R,[c("color",e)]:Z,[c("textColor",e)]:ee,[c("border",e)]:oe,[c("closeIconColor",e)]:P,[c("closeIconColorHover",e)]:re,[c("closeIconColorPressed",e)]:ae,[c("closeColorHover",e)]:ce,[c("closeColorPressed",e)]:ne}}=C.value,m=ue(O);return{"--n-font-weight-strong":G,"--n-avatar-size-override":`calc(${R} - 8px)`,"--n-bezier":S,"--n-border-radius":j,"--n-border":oe,"--n-close-icon-size":X,"--n-close-color-pressed":ne,"--n-close-color-hover":ce,"--n-close-border-radius":q,"--n-close-icon-color":P,"--n-close-icon-color-hover":re,"--n-close-icon-color-pressed":ae,"--n-close-icon-color-disabled":P,"--n-close-margin-top":m.top,"--n-close-margin-right":m.right,"--n-close-margin-bottom":m.bottom,"--n-close-margin-left":m.left,"--n-close-size":Q,"--n-color":a||(o.value?J:Z),"--n-color-checkable":D,"--n-color-checked":W,"--n-color-checked-hover":A,"--n-color-checked-pressed":L,"--n-color-hover-checkable":K,"--n-color-pressed-checkable":V,"--n-font-size":Y,"--n-height":R,"--n-opacity-disabled":F,"--n-padding":w,"--n-text-color":s||ee,"--n-text-color-checkable":H,"--n-text-color-checked":U,"--n-text-color-hover-checkable":N,"--n-text-color-pressed-checkable":E}}),g=k?ge("tag",B(()=>{let e="";const{type:a,color:{color:s,textColor:n}={}}=r;return e+=a[0],e+=h.value[0],s&&(e+=`a${I(s)}`),n&&(e+=`b${I(n)}`),o.value&&(e+="c"),e}),$,r):void 0;return Object.assign(Object.assign({},t),{rtlEnabled:M,mergedClsPrefix:u,contentRef:i,mergedBordered:o,handleClick:f,handleCloseClick:p,cssVars:k?void 0:$,themeClass:g?.themeClass,onRender:g?.onRender})},render(){var r,i;const{mergedClsPrefix:o,rtlEnabled:u,closable:k,color:{borderColor:y}={},round:d,onRender:h,$slots:C}=this;h?.();const f=_(C.avatar,t=>t&&v("div",{class:`${o}-tag__avatar`},t)),p=_(C.icon,t=>t&&v("div",{class:`${o}-tag__icon`},t));return v("div",{class:[`${o}-tag`,this.themeClass,{[`${o}-tag--rtl`]:u,[`${o}-tag--strong`]:this.strong,[`${o}-tag--disabled`]:this.disabled,[`${o}-tag--checkable`]:this.checkable,[`${o}-tag--checked`]:this.checkable&&this.checked,[`${o}-tag--round`]:d,[`${o}-tag--avatar`]:f,[`${o}-tag--icon`]:p,[`${o}-tag--closable`]:k}],style:this.cssVars,onClick:this.handleClick,onMouseenter:this.onMouseenter,onMouseleave:this.onMouseleave},p||f,v("span",{class:`${o}-tag__content`,ref:"contentRef"},(i=(r=this.$slots).default)===null||i===void 0?void 0:i.call(r)),!this.checkable&&k?v(se,{clsPrefix:o,class:`${o}-tag__close`,disabled:this.disabled,onClick:this.handleCloseClick,focusable:this.internalCloseFocusable,round:d,isButtonTag:this.internalCloseIsButtonTag,absolute:!0}):null,!this.checkable&&this.mergedBordered?v("div",{class:`${o}-tag__border`,style:{borderColor:y}}):null)}});export{Be as N};
