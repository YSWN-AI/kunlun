import{d as M,h,a1 as U,ad as x,ab as f,an as y,ac as p,az as L,bJ as He,bg as K,a4 as Ee,T as F,v as b,aa as ee,aE as Te,at as Q,ak as V,F as Fe,a0 as J,bK as Me,r as O,aP as Oe,a7 as Ke,ag as me,bL as ke,w as ce,am as de,a8 as Le,aw as _e,aI as $e,a9 as se,bk as je,ai as E}from"./index-wHqlCVHi.js";import{N as Be}from"./Dropdown-D1yC9Rtu.js";import{V as De,c as Z}from"./create-DyFs6GM1.js";const Ve=M({name:"ChevronDownFilled",render(){return h("svg",{viewBox:"0 0 16 16",fill:"none",xmlns:"http://www.w3.org/2000/svg"},h("path",{d:"M3.20041 5.73966C3.48226 5.43613 3.95681 5.41856 4.26034 5.70041L8 9.22652L11.7397 5.70041C12.0432 5.41856 12.5177 5.43613 12.7996 5.73966C13.0815 6.0432 13.0639 6.51775 12.7603 6.7996L8.51034 10.7996C8.22258 11.0668 7.77743 11.0668 7.48967 10.7996L3.23966 6.7996C2.93613 6.51775 2.91856 6.0432 3.20041 5.73966Z",fill:"currentColor"}))}}),Ue=U("n-layout-sider"),_=U("n-menu"),he=U("n-submenu"),oe=U("n-menu-item-group"),ue=[x("&::before","background-color: var(--n-item-color-hover);"),p("arrow",`
 color: var(--n-arrow-color-hover);
 `),p("icon",`
 color: var(--n-item-icon-color-hover);
 `),f("menu-item-content-header",`
 color: var(--n-item-text-color-hover);
 `,[x("a",`
 color: var(--n-item-text-color-hover);
 `),p("extra",`
 color: var(--n-item-text-color-hover);
 `)])],ve=[p("icon",`
 color: var(--n-item-icon-color-hover-horizontal);
 `),f("menu-item-content-header",`
 color: var(--n-item-text-color-hover-horizontal);
 `,[x("a",`
 color: var(--n-item-text-color-hover-horizontal);
 `),p("extra",`
 color: var(--n-item-text-color-hover-horizontal);
 `)])],Ge=x([f("menu",`
 background-color: var(--n-color);
 color: var(--n-item-text-color);
 overflow: hidden;
 transition: background-color .3s var(--n-bezier);
 box-sizing: border-box;
 font-size: var(--n-font-size);
 padding-bottom: 6px;
 `,[y("horizontal",`
 max-width: 100%;
 width: 100%;
 display: flex;
 overflow: hidden;
 padding-bottom: 0;
 `,[f("submenu","margin: 0;"),f("menu-item","margin: 0;"),f("menu-item-content",`
 padding: 0 20px;
 border-bottom: 2px solid #0000;
 `,[x("&::before","display: none;"),y("selected","border-bottom: 2px solid var(--n-border-color-horizontal)")]),f("menu-item-content",[y("selected",[p("icon","color: var(--n-item-icon-color-active-horizontal);"),f("menu-item-content-header",`
 color: var(--n-item-text-color-active-horizontal);
 `,[x("a","color: var(--n-item-text-color-active-horizontal);"),p("extra","color: var(--n-item-text-color-active-horizontal);")])]),y("child-active",`
 border-bottom: 2px solid var(--n-border-color-horizontal);
 `,[f("menu-item-content-header",`
 color: var(--n-item-text-color-child-active-horizontal);
 `,[x("a",`
 color: var(--n-item-text-color-child-active-horizontal);
 `),p("extra",`
 color: var(--n-item-text-color-child-active-horizontal);
 `)]),p("icon",`
 color: var(--n-item-icon-color-child-active-horizontal);
 `)]),L("disabled",[L("selected, child-active",[x("&:focus-within",ve)]),y("selected",[T(null,[p("icon","color: var(--n-item-icon-color-active-hover-horizontal);"),f("menu-item-content-header",`
 color: var(--n-item-text-color-active-hover-horizontal);
 `,[x("a","color: var(--n-item-text-color-active-hover-horizontal);"),p("extra","color: var(--n-item-text-color-active-hover-horizontal);")])])]),y("child-active",[T(null,[p("icon","color: var(--n-item-icon-color-child-active-hover-horizontal);"),f("menu-item-content-header",`
 color: var(--n-item-text-color-child-active-hover-horizontal);
 `,[x("a","color: var(--n-item-text-color-child-active-hover-horizontal);"),p("extra","color: var(--n-item-text-color-child-active-hover-horizontal);")])])]),T("border-bottom: 2px solid var(--n-border-color-horizontal);",ve)]),f("menu-item-content-header",[x("a","color: var(--n-item-text-color-horizontal);")])])]),L("responsive",[f("menu-item-content-header",`
 overflow: hidden;
 text-overflow: ellipsis;
 `)]),y("collapsed",[f("menu-item-content",[y("selected",[x("&::before",`
 background-color: var(--n-item-color-active-collapsed) !important;
 `)]),f("menu-item-content-header","opacity: 0;"),p("arrow","opacity: 0;"),p("icon","color: var(--n-item-icon-color-collapsed);")])]),f("menu-item",`
 height: var(--n-item-height);
 margin-top: 6px;
 position: relative;
 `),f("menu-item-content",`
 box-sizing: border-box;
 line-height: 1.75;
 height: 100%;
 display: grid;
 grid-template-areas: "icon content arrow";
 grid-template-columns: auto 1fr auto;
 align-items: center;
 cursor: pointer;
 position: relative;
 padding-right: 18px;
 transition:
 background-color .3s var(--n-bezier),
 padding-left .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 `,[x("> *","z-index: 1;"),x("&::before",`
 z-index: auto;
 content: "";
 background-color: #0000;
 position: absolute;
 left: 8px;
 right: 8px;
 top: 0;
 bottom: 0;
 pointer-events: none;
 border-radius: var(--n-border-radius);
 transition: background-color .3s var(--n-bezier);
 `),y("disabled",`
 opacity: .45;
 cursor: not-allowed;
 `),y("collapsed",[p("arrow","transform: rotate(0);")]),y("selected",[x("&::before","background-color: var(--n-item-color-active);"),p("arrow","color: var(--n-arrow-color-active);"),p("icon","color: var(--n-item-icon-color-active);"),f("menu-item-content-header",`
 color: var(--n-item-text-color-active);
 `,[x("a","color: var(--n-item-text-color-active);"),p("extra","color: var(--n-item-text-color-active);")])]),y("child-active",[f("menu-item-content-header",`
 color: var(--n-item-text-color-child-active);
 `,[x("a",`
 color: var(--n-item-text-color-child-active);
 `),p("extra",`
 color: var(--n-item-text-color-child-active);
 `)]),p("arrow",`
 color: var(--n-arrow-color-child-active);
 `),p("icon",`
 color: var(--n-item-icon-color-child-active);
 `)]),L("disabled",[L("selected, child-active",[x("&:focus-within",ue)]),y("selected",[T(null,[p("arrow","color: var(--n-arrow-color-active-hover);"),p("icon","color: var(--n-item-icon-color-active-hover);"),f("menu-item-content-header",`
 color: var(--n-item-text-color-active-hover);
 `,[x("a","color: var(--n-item-text-color-active-hover);"),p("extra","color: var(--n-item-text-color-active-hover);")])])]),y("child-active",[T(null,[p("arrow","color: var(--n-arrow-color-child-active-hover);"),p("icon","color: var(--n-item-icon-color-child-active-hover);"),f("menu-item-content-header",`
 color: var(--n-item-text-color-child-active-hover);
 `,[x("a","color: var(--n-item-text-color-child-active-hover);"),p("extra","color: var(--n-item-text-color-child-active-hover);")])])]),y("selected",[T(null,[x("&::before","background-color: var(--n-item-color-active-hover);")])]),T(null,ue)]),p("icon",`
 grid-area: icon;
 color: var(--n-item-icon-color);
 transition:
 color .3s var(--n-bezier),
 font-size .3s var(--n-bezier),
 margin-right .3s var(--n-bezier);
 box-sizing: content-box;
 display: inline-flex;
 align-items: center;
 justify-content: center;
 `),p("arrow",`
 grid-area: arrow;
 font-size: 16px;
 color: var(--n-arrow-color);
 transform: rotate(180deg);
 opacity: 1;
 transition:
 color .3s var(--n-bezier),
 transform 0.2s var(--n-bezier),
 opacity 0.2s var(--n-bezier);
 `),f("menu-item-content-header",`
 grid-area: content;
 transition:
 color .3s var(--n-bezier),
 opacity .3s var(--n-bezier);
 opacity: 1;
 white-space: nowrap;
 color: var(--n-item-text-color);
 `,[x("a",`
 outline: none;
 text-decoration: none;
 transition: color .3s var(--n-bezier);
 color: var(--n-item-text-color);
 `,[x("&::before",`
 content: "";
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 `)]),p("extra",`
 font-size: .93em;
 color: var(--n-group-text-color);
 transition: color .3s var(--n-bezier);
 `)])]),f("submenu",`
 cursor: pointer;
 position: relative;
 margin-top: 6px;
 `,[f("menu-item-content",`
 height: var(--n-item-height);
 `),f("submenu-children",`
 overflow: hidden;
 padding: 0;
 `,[He({duration:".2s"})])]),f("menu-item-group",[f("menu-item-group-title",`
 margin-top: 6px;
 color: var(--n-group-text-color);
 cursor: default;
 font-size: .93em;
 height: 36px;
 display: flex;
 align-items: center;
 transition:
 padding-left .3s var(--n-bezier),
 color .3s var(--n-bezier);
 `)])]),f("menu-tooltip",[x("a",`
 color: inherit;
 text-decoration: none;
 `)]),f("menu-divider",`
 transition: background-color .3s var(--n-bezier);
 background-color: var(--n-divider-color);
 height: 1px;
 margin: 6px 18px;
 `)]);function T(e,n){return[y("hover",e,n),x("&:hover",e,n)]}const pe=M({name:"MenuOptionContent",props:{collapsed:Boolean,disabled:Boolean,title:[String,Function],icon:Function,extra:[String,Function],showArrow:Boolean,childActive:Boolean,hover:Boolean,paddingLeft:Number,selected:Boolean,maxIconSize:{type:Number,required:!0},activeIconSize:{type:Number,required:!0},iconMarginRight:{type:Number,required:!0},clsPrefix:{type:String,required:!0},onClick:Function,tmNode:{type:Object,required:!0},isEllipsisPlaceholder:Boolean},setup(e){const{props:n}=F(_);return{menuProps:n,style:b(()=>{const{paddingLeft:r}=e;return{paddingLeft:r&&`${r}px`}}),iconStyle:b(()=>{const{maxIconSize:r,activeIconSize:d,iconMarginRight:a}=e;return{width:`${r}px`,height:`${r}px`,fontSize:`${d}px`,marginRight:`${a}px`}})}},render(){const{clsPrefix:e,tmNode:n,menuProps:{renderIcon:r,renderLabel:d,renderExtra:a,expandIcon:c}}=this,v=r?r(n.rawNode):K(this.icon);return h("div",{onClick:g=>{var s;(s=this.onClick)===null||s===void 0||s.call(this,g)},role:"none",class:[`${e}-menu-item-content`,{[`${e}-menu-item-content--selected`]:this.selected,[`${e}-menu-item-content--collapsed`]:this.collapsed,[`${e}-menu-item-content--child-active`]:this.childActive,[`${e}-menu-item-content--disabled`]:this.disabled,[`${e}-menu-item-content--hover`]:this.hover}],style:this.style},v&&h("div",{class:`${e}-menu-item-content__icon`,style:this.iconStyle,role:"none"},[v]),h("div",{class:`${e}-menu-item-content-header`,role:"none"},this.isEllipsisPlaceholder?this.title:d?d(n.rawNode):K(this.title),this.extra||a?h("span",{class:`${e}-menu-item-content-header__extra`}," ",a?a(n.rawNode):K(this.extra)):null),this.showArrow?h(Ee,{ariaHidden:!0,class:`${e}-menu-item-content__arrow`,clsPrefix:e},{default:()=>c?c(n.rawNode):h(Ve,null)}):null)}}),D=8;function te(e){const n=F(_),{props:r,mergedCollapsedRef:d}=n,a=F(he,null),c=F(oe,null),v=b(()=>r.mode==="horizontal"),g=b(()=>v.value?r.dropdownPlacement:"tmNodes"in e?"right-start":"right"),s=b(()=>{var u;return Math.max((u=r.collapsedIconSize)!==null&&u!==void 0?u:r.iconSize,r.iconSize)}),C=b(()=>{var u;return!v.value&&e.root&&d.value&&(u=r.collapsedIconSize)!==null&&u!==void 0?u:r.iconSize}),R=b(()=>{if(v.value)return;const{collapsedWidth:u,indent:I,rootIndent:A}=r,{root:N,isGroup:P}=e,H=A===void 0?I:A;return N?d.value?u/2-s.value/2:H:c&&typeof c.paddingLeftRef.value=="number"?I/2+c.paddingLeftRef.value:a&&typeof a.paddingLeftRef.value=="number"?(P?I/2:I)+a.paddingLeftRef.value:0}),w=b(()=>{const{collapsedWidth:u,indent:I,rootIndent:A}=r,{value:N}=s,{root:P}=e;return v.value||!P||!d.value?D:(A===void 0?I:A)+N+D-(u+N)/2});return{dropdownPlacement:g,activeIconSize:C,maxIconSize:s,paddingLeft:R,iconMarginRight:w,NMenu:n,NSubmenu:a,NMenuOptionGroup:c}}const re={internalKey:{type:[String,Number],required:!0},root:Boolean,isGroup:Boolean,level:{type:Number,required:!0},title:[String,Function],extra:[String,Function]},qe=M({name:"MenuDivider",setup(){const e=F(_),{mergedClsPrefixRef:n,isHorizontalRef:r}=e;return()=>r.value?null:h("div",{class:`${n.value}-menu-divider`})}}),fe=Object.assign(Object.assign({},re),{tmNode:{type:Object,required:!0},disabled:Boolean,icon:Function,onClick:Function}),We=ee(fe),Je=M({name:"MenuOption",props:fe,setup(e){const n=te(e),{NSubmenu:r,NMenu:d,NMenuOptionGroup:a}=n,{props:c,mergedClsPrefixRef:v,mergedCollapsedRef:g}=d,s=r?r.mergedDisabledRef:a?a.mergedDisabledRef:{value:!1},C=b(()=>s.value||e.disabled);function R(u){const{onClick:I}=e;I&&I(u)}function w(u){C.value||(d.doSelect(e.internalKey,e.tmNode.rawNode),R(u))}return{mergedClsPrefix:v,dropdownPlacement:n.dropdownPlacement,paddingLeft:n.paddingLeft,iconMarginRight:n.iconMarginRight,maxIconSize:n.maxIconSize,activeIconSize:n.activeIconSize,mergedTheme:d.mergedThemeRef,menuProps:c,dropdownEnabled:Q(()=>e.root&&g.value&&c.mode!=="horizontal"&&!C.value),selected:Q(()=>d.mergedValueRef.value===e.internalKey),mergedDisabled:C,handleClick:w}},render(){const{mergedClsPrefix:e,mergedTheme:n,tmNode:r,menuProps:{renderLabel:d,nodeProps:a}}=this,c=a?.(r.rawNode);return h("div",Object.assign({},c,{role:"menuitem",class:[`${e}-menu-item`,c?.class]}),h(Te,{theme:n.peers.Tooltip,themeOverrides:n.peerOverrides.Tooltip,trigger:"hover",placement:this.dropdownPlacement,disabled:!this.dropdownEnabled||this.title===void 0,internalExtraClass:["menu-tooltip"]},{default:()=>d?d(r.rawNode):K(this.title),trigger:()=>h(pe,{tmNode:r,clsPrefix:e,paddingLeft:this.paddingLeft,iconMarginRight:this.iconMarginRight,maxIconSize:this.maxIconSize,activeIconSize:this.activeIconSize,selected:this.selected,title:this.title,extra:this.extra,disabled:this.mergedDisabled,icon:this.icon,onClick:this.handleClick})}))}}),ge=Object.assign(Object.assign({},re),{tmNode:{type:Object,required:!0},tmNodes:{type:Array,required:!0}}),Ze=ee(ge),Qe=M({name:"MenuOptionGroup",props:ge,setup(e){const n=te(e),{NSubmenu:r}=n,d=b(()=>r?.mergedDisabledRef.value?!0:e.tmNode.disabled);V(oe,{paddingLeftRef:n.paddingLeft,mergedDisabledRef:d});const{mergedClsPrefixRef:a,props:c}=F(_);return function(){const{value:v}=a,g=n.paddingLeft.value,{nodeProps:s}=c,C=s?.(e.tmNode.rawNode);return h("div",{class:`${v}-menu-item-group`,role:"group"},h("div",Object.assign({},C,{class:[`${v}-menu-item-group-title`,C?.class],style:[C?.style||"",g!==void 0?`padding-left: ${g}px;`:""]}),K(e.title),e.extra?h(Fe,null," ",K(e.extra)):null),h("div",null,e.tmNodes.map(R=>ne(R,c))))}}});function X(e){return e.type==="divider"||e.type==="render"}function Xe(e){return e.type==="divider"}function ne(e,n){const{rawNode:r}=e,{show:d}=r;if(d===!1)return null;if(X(r))return Xe(r)?h(qe,Object.assign({key:e.key},r.props)):null;const{labelField:a}=n,{key:c,level:v,isGroup:g}=e,s=Object.assign(Object.assign({},r),{title:r.title||r[a],extra:r.titleExtra||r.extra,key:c,internalKey:c,level:v,root:v===0,isGroup:g});return e.children?e.isGroup?h(Qe,J(s,Ze,{tmNode:e,tmNodes:e.children,key:c})):h(Y,J(s,Ye,{key:c,rawNodes:r[n.childrenField],tmNodes:e.children,tmNode:e})):h(Je,J(s,We,{key:c,tmNode:e}))}const xe=Object.assign(Object.assign({},re),{rawNodes:{type:Array,default:()=>[]},tmNodes:{type:Array,default:()=>[]},tmNode:{type:Object,required:!0},disabled:Boolean,icon:Function,onClick:Function,domId:String,virtualChildActive:{type:Boolean,default:void 0},isEllipsisPlaceholder:Boolean}),Ye=ee(xe),Y=M({name:"Submenu",props:xe,setup(e){const n=te(e),{NMenu:r,NSubmenu:d}=n,{props:a,mergedCollapsedRef:c,mergedThemeRef:v}=r,g=b(()=>{const{disabled:u}=e;return d?.mergedDisabledRef.value||a.disabled?!0:u}),s=O(!1);V(he,{paddingLeftRef:n.paddingLeft,mergedDisabledRef:g}),V(oe,null);function C(){const{onClick:u}=e;u&&u()}function R(){g.value||(c.value||r.toggleExpand(e.internalKey),C())}function w(u){s.value=u}return{menuProps:a,mergedTheme:v,doSelect:r.doSelect,inverted:r.invertedRef,isHorizontal:r.isHorizontalRef,mergedClsPrefix:r.mergedClsPrefixRef,maxIconSize:n.maxIconSize,activeIconSize:n.activeIconSize,iconMarginRight:n.iconMarginRight,dropdownPlacement:n.dropdownPlacement,dropdownShow:s,paddingLeft:n.paddingLeft,mergedDisabled:g,mergedValue:r.mergedValueRef,childActive:Q(()=>{var u;return(u=e.virtualChildActive)!==null&&u!==void 0?u:r.activePathRef.value.includes(e.internalKey)}),collapsed:b(()=>a.mode==="horizontal"?!1:c.value?!0:!r.mergedExpandedKeysRef.value.includes(e.internalKey)),dropdownEnabled:b(()=>!g.value&&(a.mode==="horizontal"||c.value)),handlePopoverShowChange:w,handleClick:R}},render(){var e;const{mergedClsPrefix:n,menuProps:{renderIcon:r,renderLabel:d}}=this,a=()=>{const{isHorizontal:v,paddingLeft:g,collapsed:s,mergedDisabled:C,maxIconSize:R,activeIconSize:w,title:u,childActive:I,icon:A,handleClick:N,menuProps:{nodeProps:P},dropdownShow:H,iconMarginRight:G,tmNode:k,mergedClsPrefix:$,isEllipsisPlaceholder:q,extra:j}=this,S=P?.(k.rawNode);return h("div",Object.assign({},S,{class:[`${$}-menu-item`,S?.class],role:"menuitem"}),h(pe,{tmNode:k,paddingLeft:g,collapsed:s,disabled:C,iconMarginRight:G,maxIconSize:R,activeIconSize:w,title:u,extra:j,showArrow:!v,childActive:I,clsPrefix:$,icon:A,hover:H,onClick:N,isEllipsisPlaceholder:q}))},c=()=>h(Me,null,{default:()=>{const{tmNodes:v,collapsed:g}=this;return g?null:h("div",{class:`${n}-submenu-children`,role:"menu"},v.map(s=>ne(s,this.menuProps)))}});return this.root?h(Be,Object.assign({size:"large",trigger:"hover"},(e=this.menuProps)===null||e===void 0?void 0:e.dropdownProps,{themeOverrides:this.mergedTheme.peerOverrides.Dropdown,theme:this.mergedTheme.peers.Dropdown,builtinThemeOverrides:{fontSizeLarge:"14px",optionIconSizeLarge:"18px"},value:this.mergedValue,disabled:!this.dropdownEnabled,placement:this.dropdownPlacement,keyField:this.menuProps.keyField,labelField:this.menuProps.labelField,childrenField:this.menuProps.childrenField,onUpdateShow:this.handlePopoverShowChange,options:this.rawNodes,onSelect:this.doSelect,inverted:this.inverted,renderIcon:r,renderLabel:d}),{default:()=>h("div",{class:`${n}-submenu`,role:"menu","aria-expanded":!this.collapsed,id:this.domId},a(),this.isHorizontal?null:c())}):h("div",{class:`${n}-submenu`,role:"menu","aria-expanded":!this.collapsed,id:this.domId},a(),c())}}),eo=Object.assign(Object.assign({},me.props),{options:{type:Array,default:()=>[]},collapsed:{type:Boolean,default:void 0},collapsedWidth:{type:Number,default:48},iconSize:{type:Number,default:20},collapsedIconSize:{type:Number,default:24},rootIndent:Number,indent:{type:Number,default:32},labelField:{type:String,default:"label"},keyField:{type:String,default:"key"},childrenField:{type:String,default:"children"},disabledField:{type:String,default:"disabled"},defaultExpandAll:Boolean,defaultExpandedKeys:Array,expandedKeys:Array,value:[String,Number],defaultValue:{type:[String,Number],default:null},mode:{type:String,default:"vertical"},watchProps:{type:Array,default:void 0},disabled:Boolean,show:{type:Boolean,default:!0},inverted:Boolean,"onUpdate:expandedKeys":[Function,Array],onUpdateExpandedKeys:[Function,Array],onUpdateValue:[Function,Array],"onUpdate:value":[Function,Array],expandIcon:Function,renderIcon:Function,renderLabel:Function,renderExtra:Function,dropdownProps:Object,accordion:Boolean,nodeProps:Function,dropdownPlacement:{type:String,default:"bottom"},responsive:Boolean,items:Array,onOpenNamesChange:[Function,Array],onSelect:[Function,Array],onExpandedNamesChange:[Function,Array],expandedNames:Array,defaultExpandedNames:Array}),no=M({name:"Menu",inheritAttrs:!1,props:eo,setup(e){const{mergedClsPrefixRef:n,inlineThemeDisabled:r}=Ke(e),d=me("Menu","-menu",Ge,ke,e,n),a=F(Ue,null),c=b(()=>{var i;const{collapsed:m}=e;if(m!==void 0)return m;if(a){const{collapseModeRef:o,collapsedRef:l}=a;if(o.value==="width")return(i=l.value)!==null&&i!==void 0?i:!1}return!1}),v=b(()=>{const{keyField:i,childrenField:m,disabledField:o}=e;return Z(e.items||e.options,{getIgnored(l){return X(l)},getChildren(l){return l[m]},getDisabled(l){return l[o]},getKey(l){var z;return(z=l[i])!==null&&z!==void 0?z:l.name}})}),g=b(()=>new Set(v.value.treeNodes.map(i=>i.key))),{watchProps:s}=e,C=O(null);s?.includes("defaultValue")?ce(()=>{C.value=e.defaultValue}):C.value=e.defaultValue;const R=se(e,"value"),w=de(R,C),u=O([]),I=()=>{u.value=e.defaultExpandAll?v.value.getNonLeafKeys():e.defaultExpandedNames||e.defaultExpandedKeys||v.value.getPath(w.value,{includeSelf:!1}).keyPath};s?.includes("defaultExpandedKeys")?ce(I):I();const A=je(e,["expandedNames","expandedKeys"]),N=de(A,u),P=b(()=>v.value.treeNodes),H=b(()=>v.value.getPath(w.value).keyPath);V(_,{props:e,mergedCollapsedRef:c,mergedThemeRef:d,mergedValueRef:w,mergedExpandedKeysRef:N,activePathRef:H,mergedClsPrefixRef:n,isHorizontalRef:b(()=>e.mode==="horizontal"),invertedRef:se(e,"inverted"),doSelect:G,toggleExpand:$});function G(i,m){const{"onUpdate:value":o,onUpdateValue:l,onSelect:z}=e;l&&E(l,i,m),o&&E(o,i,m),z&&E(z,i,m),C.value=i}function k(i){const{"onUpdate:expandedKeys":m,onUpdateExpandedKeys:o,onExpandedNamesChange:l,onOpenNamesChange:z}=e;m&&E(m,i),o&&E(o,i),l&&E(l,i),z&&E(z,i),u.value=i}function $(i){const m=Array.from(N.value),o=m.findIndex(l=>l===i);if(~o)m.splice(o,1);else{if(e.accordion&&g.value.has(i)){const l=m.findIndex(z=>g.value.has(z));l>-1&&m.splice(l,1)}m.push(i)}k(m)}const q=i=>{const m=v.value.getPath(i??w.value,{includeSelf:!1}).keyPath;if(!m.length)return;const o=Array.from(N.value),l=new Set([...o,...m]);e.accordion&&g.value.forEach(z=>{l.has(z)&&!m.includes(z)&&l.delete(z)}),k(Array.from(l))},j=b(()=>{const{inverted:i}=e,{common:{cubicBezierEaseInOut:m},self:o}=d.value,{borderRadius:l,borderColorHorizontal:z,fontSize:Se,itemHeight:Ae,dividerColor:Pe}=o,t={"--n-divider-color":Pe,"--n-bezier":m,"--n-font-size":Se,"--n-border-color-horizontal":z,"--n-border-radius":l,"--n-item-height":Ae};return i?(t["--n-group-text-color"]=o.groupTextColorInverted,t["--n-color"]=o.colorInverted,t["--n-item-text-color"]=o.itemTextColorInverted,t["--n-item-text-color-hover"]=o.itemTextColorHoverInverted,t["--n-item-text-color-active"]=o.itemTextColorActiveInverted,t["--n-item-text-color-child-active"]=o.itemTextColorChildActiveInverted,t["--n-item-text-color-child-active-hover"]=o.itemTextColorChildActiveInverted,t["--n-item-text-color-active-hover"]=o.itemTextColorActiveHoverInverted,t["--n-item-icon-color"]=o.itemIconColorInverted,t["--n-item-icon-color-hover"]=o.itemIconColorHoverInverted,t["--n-item-icon-color-active"]=o.itemIconColorActiveInverted,t["--n-item-icon-color-active-hover"]=o.itemIconColorActiveHoverInverted,t["--n-item-icon-color-child-active"]=o.itemIconColorChildActiveInverted,t["--n-item-icon-color-child-active-hover"]=o.itemIconColorChildActiveHoverInverted,t["--n-item-icon-color-collapsed"]=o.itemIconColorCollapsedInverted,t["--n-item-text-color-horizontal"]=o.itemTextColorHorizontalInverted,t["--n-item-text-color-hover-horizontal"]=o.itemTextColorHoverHorizontalInverted,t["--n-item-text-color-active-horizontal"]=o.itemTextColorActiveHorizontalInverted,t["--n-item-text-color-child-active-horizontal"]=o.itemTextColorChildActiveHorizontalInverted,t["--n-item-text-color-child-active-hover-horizontal"]=o.itemTextColorChildActiveHoverHorizontalInverted,t["--n-item-text-color-active-hover-horizontal"]=o.itemTextColorActiveHoverHorizontalInverted,t["--n-item-icon-color-horizontal"]=o.itemIconColorHorizontalInverted,t["--n-item-icon-color-hover-horizontal"]=o.itemIconColorHoverHorizontalInverted,t["--n-item-icon-color-active-horizontal"]=o.itemIconColorActiveHorizontalInverted,t["--n-item-icon-color-active-hover-horizontal"]=o.itemIconColorActiveHoverHorizontalInverted,t["--n-item-icon-color-child-active-horizontal"]=o.itemIconColorChildActiveHorizontalInverted,t["--n-item-icon-color-child-active-hover-horizontal"]=o.itemIconColorChildActiveHoverHorizontalInverted,t["--n-arrow-color"]=o.arrowColorInverted,t["--n-arrow-color-hover"]=o.arrowColorHoverInverted,t["--n-arrow-color-active"]=o.arrowColorActiveInverted,t["--n-arrow-color-active-hover"]=o.arrowColorActiveHoverInverted,t["--n-arrow-color-child-active"]=o.arrowColorChildActiveInverted,t["--n-arrow-color-child-active-hover"]=o.arrowColorChildActiveHoverInverted,t["--n-item-color-hover"]=o.itemColorHoverInverted,t["--n-item-color-active"]=o.itemColorActiveInverted,t["--n-item-color-active-hover"]=o.itemColorActiveHoverInverted,t["--n-item-color-active-collapsed"]=o.itemColorActiveCollapsedInverted):(t["--n-group-text-color"]=o.groupTextColor,t["--n-color"]=o.color,t["--n-item-text-color"]=o.itemTextColor,t["--n-item-text-color-hover"]=o.itemTextColorHover,t["--n-item-text-color-active"]=o.itemTextColorActive,t["--n-item-text-color-child-active"]=o.itemTextColorChildActive,t["--n-item-text-color-child-active-hover"]=o.itemTextColorChildActiveHover,t["--n-item-text-color-active-hover"]=o.itemTextColorActiveHover,t["--n-item-icon-color"]=o.itemIconColor,t["--n-item-icon-color-hover"]=o.itemIconColorHover,t["--n-item-icon-color-active"]=o.itemIconColorActive,t["--n-item-icon-color-active-hover"]=o.itemIconColorActiveHover,t["--n-item-icon-color-child-active"]=o.itemIconColorChildActive,t["--n-item-icon-color-child-active-hover"]=o.itemIconColorChildActiveHover,t["--n-item-icon-color-collapsed"]=o.itemIconColorCollapsed,t["--n-item-text-color-horizontal"]=o.itemTextColorHorizontal,t["--n-item-text-color-hover-horizontal"]=o.itemTextColorHoverHorizontal,t["--n-item-text-color-active-horizontal"]=o.itemTextColorActiveHorizontal,t["--n-item-text-color-child-active-horizontal"]=o.itemTextColorChildActiveHorizontal,t["--n-item-text-color-child-active-hover-horizontal"]=o.itemTextColorChildActiveHoverHorizontal,t["--n-item-text-color-active-hover-horizontal"]=o.itemTextColorActiveHoverHorizontal,t["--n-item-icon-color-horizontal"]=o.itemIconColorHorizontal,t["--n-item-icon-color-hover-horizontal"]=o.itemIconColorHoverHorizontal,t["--n-item-icon-color-active-horizontal"]=o.itemIconColorActiveHorizontal,t["--n-item-icon-color-active-hover-horizontal"]=o.itemIconColorActiveHoverHorizontal,t["--n-item-icon-color-child-active-horizontal"]=o.itemIconColorChildActiveHorizontal,t["--n-item-icon-color-child-active-hover-horizontal"]=o.itemIconColorChildActiveHoverHorizontal,t["--n-arrow-color"]=o.arrowColor,t["--n-arrow-color-hover"]=o.arrowColorHover,t["--n-arrow-color-active"]=o.arrowColorActive,t["--n-arrow-color-active-hover"]=o.arrowColorActiveHover,t["--n-arrow-color-child-active"]=o.arrowColorChildActive,t["--n-arrow-color-child-active-hover"]=o.arrowColorChildActiveHover,t["--n-item-color-hover"]=o.itemColorHover,t["--n-item-color-active"]=o.itemColorActive,t["--n-item-color-active-hover"]=o.itemColorActiveHover,t["--n-item-color-active-collapsed"]=o.itemColorActiveCollapsed),t}),S=r?Le("menu",b(()=>e.inverted?"a":"b"),j,e):void 0,W=_e(),ie=O(null),be=O(null);let le=!0;const ae=()=>{var i;le?le=!1:(i=ie.value)===null||i===void 0||i.sync({showAllItemsBeforeCalculate:!0})};function Ce(){return document.getElementById(W)}const B=O(-1);function ze(i){B.value=e.options.length-i}function ye(i){i||(B.value=-1)}const Ie=b(()=>{const i=B.value;return{children:i===-1?[]:e.options.slice(i)}}),we=b(()=>{const{childrenField:i,disabledField:m,keyField:o}=e;return Z([Ie.value],{getIgnored(l){return X(l)},getChildren(l){return l[i]},getDisabled(l){return l[m]},getKey(l){var z;return(z=l[o])!==null&&z!==void 0?z:l.name}})}),Re=b(()=>Z([{}]).treeNodes[0]);function Ne(){var i;if(B.value===-1)return h(Y,{root:!0,level:0,key:"__ellpisisGroupPlaceholder__",internalKey:"__ellpisisGroupPlaceholder__",title:"···",tmNode:Re.value,domId:W,isEllipsisPlaceholder:!0});const m=we.value.treeNodes[0],o=H.value,l=!!(!((i=m.children)===null||i===void 0)&&i.some(z=>o.includes(z.key)));return h(Y,{level:0,root:!0,key:"__ellpisisGroup__",internalKey:"__ellpisisGroup__",title:"···",virtualChildActive:l,tmNode:m,domId:W,rawNodes:m.rawNode.children||[],tmNodes:m.children||[],isEllipsisPlaceholder:!0})}return{mergedClsPrefix:n,controlledExpandedKeys:A,uncontrolledExpanededKeys:u,mergedExpandedKeys:N,uncontrolledValue:C,mergedValue:w,activePath:H,tmNodes:P,mergedTheme:d,mergedCollapsed:c,cssVars:r?void 0:j,themeClass:S?.themeClass,overflowRef:ie,counterRef:be,updateCounter:()=>{},onResize:ae,onUpdateOverflow:ye,onUpdateCount:ze,renderCounter:Ne,getCounter:Ce,onRender:S?.onRender,showOption:q,deriveResponsiveState:ae}},render(){const{mergedClsPrefix:e,mode:n,themeClass:r,onRender:d}=this;d?.();const a=()=>this.tmNodes.map(s=>ne(s,this.$props)),v=n==="horizontal"&&this.responsive,g=()=>h("div",$e(this.$attrs,{role:n==="horizontal"?"menubar":"menu",class:[`${e}-menu`,r,`${e}-menu--${n}`,v&&`${e}-menu--responsive`,this.mergedCollapsed&&`${e}-menu--collapsed`],style:this.cssVars}),v?h(De,{ref:"overflowRef",onUpdateOverflow:this.onUpdateOverflow,getCounter:this.getCounter,onUpdateCount:this.onUpdateCount,updateCounter:this.updateCounter,style:{width:"100%",display:"flex",overflow:"hidden"}},{default:a,counter:this.renderCounter}):a());return v?h(Oe,{onResize:this.onResize},{default:g}):g()}});export{no as N};
