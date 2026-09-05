import{ab as we,ac as u,ao as _e,ad as he,an as O,az as ke,d as Fe,bA as fe,h as k,a3 as X,as as Ne,aL as Ve,a7 as Te,ag as Re,bB as De,al as Oe,r as d,am as Pe,a8 as Ue,v as se,a9 as Ie,ax as G,aO as pe,aC as P,ai as me,I as Me,D as Ae,o as p,c as m,a as s,j as r,u as l,bC as ye,N as j,x as ee,k as w,A as xe,i as Ke,B as ie,C as ze,F as Ce,l as Se,t as x,s as ne,K as te,J as je,R as be,_ as We}from"./index-wHqlCVHi.js";import{C as Ee}from"./CloudUploadOutlined-BcxDM5Nd.js";import{F as $e}from"./FileTextOutlined-B6YA9enG.js";import{R as Le}from"./RestOutlined-BMJfru-Q.js";import{C as He,F as Xe}from"./FileOutlined-DjigiGaY.js";import{N as Ge}from"./Divider-Dr4Bo1Bj.js";import{N as ge}from"./Select-1IsvWhSe.js";import{N as Je}from"./Input-DkuEDZVa.js";import{N as Ye}from"./Tag-CodsH--1.js";import{N as qe}from"./Progress-1OnFMlCy.js";import"./Suffix-DzKYYMWH.js";import"./create-DyFs6GM1.js";import"./Empty-C1m5NISZ.js";const Qe=we("switch",`
 height: var(--n-height);
 min-width: var(--n-width);
 vertical-align: middle;
 user-select: none;
 -webkit-user-select: none;
 display: inline-flex;
 outline: none;
 justify-content: center;
 align-items: center;
`,[u("children-placeholder",`
 height: var(--n-rail-height);
 display: flex;
 flex-direction: column;
 overflow: hidden;
 pointer-events: none;
 visibility: hidden;
 `),u("rail-placeholder",`
 display: flex;
 flex-wrap: none;
 `),u("button-placeholder",`
 width: calc(1.75 * var(--n-rail-height));
 height: var(--n-rail-height);
 `),we("base-loading",`
 position: absolute;
 top: 50%;
 left: 50%;
 transform: translateX(-50%) translateY(-50%);
 font-size: calc(var(--n-button-width) - 4px);
 color: var(--n-loading-color);
 transition: color .3s var(--n-bezier);
 `,[_e({left:"50%",top:"50%",originalTransform:"translateX(-50%) translateY(-50%)"})]),u("checked, unchecked",`
 transition: color .3s var(--n-bezier);
 color: var(--n-text-color);
 box-sizing: border-box;
 position: absolute;
 white-space: nowrap;
 top: 0;
 bottom: 0;
 display: flex;
 align-items: center;
 line-height: 1;
 `),u("checked",`
 right: 0;
 padding-right: calc(1.25 * var(--n-rail-height) - var(--n-offset));
 `),u("unchecked",`
 left: 0;
 justify-content: flex-end;
 padding-left: calc(1.25 * var(--n-rail-height) - var(--n-offset));
 `),he("&:focus",[u("rail",`
 box-shadow: var(--n-box-shadow-focus);
 `)]),O("round",[u("rail","border-radius: calc(var(--n-rail-height) / 2);",[u("button","border-radius: calc(var(--n-button-height) / 2);")])]),ke("disabled",[ke("icon",[O("rubber-band",[O("pressed",[u("rail",[u("button","max-width: var(--n-button-width-pressed);")])]),u("rail",[he("&:active",[u("button","max-width: var(--n-button-width-pressed);")])]),O("active",[O("pressed",[u("rail",[u("button","left: calc(100% - var(--n-offset) - var(--n-button-width-pressed));")])]),u("rail",[he("&:active",[u("button","left: calc(100% - var(--n-offset) - var(--n-button-width-pressed));")])])])])])]),O("active",[u("rail",[u("button","left: calc(100% - var(--n-button-width) - var(--n-offset))")])]),u("rail",`
 overflow: hidden;
 height: var(--n-rail-height);
 min-width: var(--n-rail-width);
 border-radius: var(--n-rail-border-radius);
 cursor: pointer;
 position: relative;
 transition:
 opacity .3s var(--n-bezier),
 background .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier);
 background-color: var(--n-rail-color);
 `,[u("button-icon",`
 color: var(--n-icon-color);
 transition: color .3s var(--n-bezier);
 font-size: calc(var(--n-button-height) - 4px);
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 display: flex;
 justify-content: center;
 align-items: center;
 line-height: 1;
 `,[_e()]),u("button",`
 align-items: center; 
 top: var(--n-offset);
 left: var(--n-offset);
 height: var(--n-button-height);
 width: var(--n-button-width-pressed);
 max-width: var(--n-button-width);
 border-radius: var(--n-button-border-radius);
 background-color: var(--n-button-color);
 box-shadow: var(--n-button-box-shadow);
 box-sizing: border-box;
 cursor: inherit;
 content: "";
 position: absolute;
 transition:
 background-color .3s var(--n-bezier),
 left .3s var(--n-bezier),
 opacity .3s var(--n-bezier),
 max-width .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier);
 `)]),O("active",[u("rail","background-color: var(--n-rail-color-active);")]),O("loading",[u("rail",`
 cursor: wait;
 `)]),O("disabled",[u("rail",`
 cursor: not-allowed;
 opacity: .5;
 `)])]),Ze=Object.assign(Object.assign({},Re.props),{size:String,value:{type:[String,Number,Boolean],default:void 0},loading:Boolean,defaultValue:{type:[String,Number,Boolean],default:!1},disabled:{type:Boolean,default:void 0},round:{type:Boolean,default:!0},"onUpdate:value":[Function,Array],onUpdateValue:[Function,Array],checkedValue:{type:[String,Number,Boolean],default:!0},uncheckedValue:{type:[String,Number,Boolean],default:!1},railStyle:Function,rubberBand:{type:Boolean,default:!0},spinProps:Object,onChange:[Function,Array]});let ae;const Be=Fe({name:"Switch",props:Ze,slots:Object,setup(t){ae===void 0&&(typeof CSS<"u"?typeof CSS.supports<"u"?ae=CSS.supports("width","max(1px)"):ae=!1:ae=!0);const{mergedClsPrefixRef:U,inlineThemeDisabled:W,mergedComponentPropsRef:h}=Te(t),$=Re("Switch","-switch",Qe,De,t,U),y=Oe(t,{mergedSize(n){var F,R;if(t.size!==void 0)return t.size;if(n)return n.mergedSize.value;const D=(R=(F=h?.value)===null||F===void 0?void 0:F.Switch)===null||R===void 0?void 0:R.size;return D||"medium"}}),{mergedSizeRef:z,mergedDisabledRef:C}=y,I=d(t.defaultValue),E=Ie(t,"value"),_=Pe(E,I),V=se(()=>_.value===t.checkedValue),c=d(!1),g=d(!1),f=se(()=>{const{railStyle:n}=t;if(n)return n({focused:g.value,checked:V.value})});function B(n){const{"onUpdate:value":F,onChange:R,onUpdateValue:D}=t,{nTriggerFormInput:Z,nTriggerFormChange:K}=y;F&&me(F,n),D&&me(D,n),R&&me(R,n),I.value=n,Z(),K()}function M(){const{nTriggerFormFocus:n}=y;n()}function T(){const{nTriggerFormBlur:n}=y;n()}function L(){t.loading||C.value||(_.value!==t.checkedValue?B(t.checkedValue):B(t.uncheckedValue))}function q(){g.value=!0,M()}function J(){g.value=!1,T(),c.value=!1}function re(n){t.loading||C.value||n.key===" "&&(_.value!==t.checkedValue?B(t.checkedValue):B(t.uncheckedValue),c.value=!1)}function ue(n){t.loading||C.value||n.key===" "&&(n.preventDefault(),c.value=!0)}const Q=se(()=>{const{value:n}=z,{self:{opacityDisabled:F,railColor:R,railColorActive:D,buttonBoxShadow:Z,buttonColor:K,boxShadowFocus:oe,loadingColor:le,textColor:ce,iconColor:de,[G("buttonHeight",n)]:N,[G("buttonWidth",n)]:o,[G("buttonWidthPressed",n)]:e,[G("railHeight",n)]:v,[G("railWidth",n)]:a,[G("railBorderRadius",n)]:i,[G("buttonBorderRadius",n)]:b},common:{cubicBezierEaseInOut:S}}=$.value;let H,Y,ve;return ae?(H=`calc((${v} - ${N}) / 2)`,Y=`max(${v}, ${N})`,ve=`max(${a}, calc(${a} + ${N} - ${v}))`):(H=pe((P(v)-P(N))/2),Y=pe(Math.max(P(v),P(N))),ve=P(v)>P(N)?a:pe(P(a)+P(N)-P(v))),{"--n-bezier":S,"--n-button-border-radius":b,"--n-button-box-shadow":Z,"--n-button-color":K,"--n-button-width":o,"--n-button-width-pressed":e,"--n-button-height":N,"--n-height":Y,"--n-offset":H,"--n-opacity-disabled":F,"--n-rail-border-radius":i,"--n-rail-color":R,"--n-rail-color-active":D,"--n-rail-height":v,"--n-rail-width":a,"--n-width":ve,"--n-box-shadow-focus":oe,"--n-loading-color":le,"--n-text-color":ce,"--n-icon-color":de}}),A=W?Ue("switch",se(()=>z.value[0]),Q,t):void 0;return{handleClick:L,handleBlur:J,handleFocus:q,handleKeyup:re,handleKeydown:ue,mergedRailStyle:f,pressed:c,mergedClsPrefix:U,mergedValue:_,checked:V,mergedDisabled:C,cssVars:W?void 0:Q,themeClass:A?.themeClass,onRender:A?.onRender}},render(){const{mergedClsPrefix:t,mergedDisabled:U,checked:W,mergedRailStyle:h,onRender:$,$slots:y}=this;$?.();const{checked:z,unchecked:C,icon:I,"checked-icon":E,"unchecked-icon":_}=y,V=!(fe(I)&&fe(E)&&fe(_));return k("div",{role:"switch","aria-checked":W,class:[`${t}-switch`,this.themeClass,V&&`${t}-switch--icon`,W&&`${t}-switch--active`,U&&`${t}-switch--disabled`,this.round&&`${t}-switch--round`,this.loading&&`${t}-switch--loading`,this.pressed&&`${t}-switch--pressed`,this.rubberBand&&`${t}-switch--rubber-band`],tabindex:this.mergedDisabled?void 0:0,style:this.cssVars,onClick:this.handleClick,onFocus:this.handleFocus,onBlur:this.handleBlur,onKeyup:this.handleKeyup,onKeydown:this.handleKeydown},k("div",{class:`${t}-switch__rail`,"aria-hidden":"true",style:h},X(z,c=>X(C,g=>c||g?k("div",{"aria-hidden":!0,class:`${t}-switch__children-placeholder`},k("div",{class:`${t}-switch__rail-placeholder`},k("div",{class:`${t}-switch__button-placeholder`}),c),k("div",{class:`${t}-switch__rail-placeholder`},k("div",{class:`${t}-switch__button-placeholder`}),g)):null)),k("div",{class:`${t}-switch__button`},X(I,c=>X(E,g=>X(_,f=>k(Ne,null,{default:()=>this.loading?k(Ve,Object.assign({key:"loading",clsPrefix:t,strokeWidth:20},this.spinProps)):this.checked&&(g||c)?k("div",{class:`${t}-switch__button-icon`,key:g?"checked-icon":"icon"},g||c):!this.checked&&(f||c)?k("div",{class:`${t}-switch__button-icon`,key:f?"unchecked-icon":"icon"},f||c):null})))),X(z,c=>c&&k("div",{key:"checked",class:`${t}-switch__checked`},c)),X(C,c=>c&&k("div",{key:"unchecked",class:`${t}-switch__unchecked`},c)))))}}),et={class:"import-view"},tt={class:"import-view__header"},at={class:"import-view__title"},st={class:"import-layout"},ot={class:"import-config"},lt={class:"file-drop-zone__content"},it={key:0,class:"selected-files"},nt={class:"selected-files__header"},rt={class:"selected-file-item__name"},ut={class:"selected-file-item__size"},ct={class:"config-row"},dt={class:"config-row"},vt={class:"config-row"},ht={class:"config-row"},ft={key:0,class:"config-row"},pt={key:1,class:"config-row"},mt={class:"import-action"},bt={key:0,class:"preview-empty"},gt={key:1,class:"preview-content"},wt={class:"preview-header"},_t={class:"preview-filename"},kt={class:"preview-body"},yt={class:"preview-text"},xt={key:0,class:"chapters-empty"},zt={key:1,class:"chapters-list"},Ct={class:"chapters-summary"},St={class:"chapters-scroll"},$t={class:"chapter-item__num"},Bt={class:"chapter-item__title"},Ft={key:0,class:"chapters-more"},Rt={key:0,class:"import-progress"},Nt={key:0,class:"progress-hint success"},Vt={key:1,class:"progress-hint error"},Tt={key:2,class:"progress-hint"},Dt={key:1,class:"disconnected-hint"},Ot=Fe({__name:"ImportView",setup(t){const U=Me(),W=U.backendConnected,h=d([]),$=d(!1),y=d(""),z=d(""),C=d("utf-8"),I=d("auto"),E=d(!0),_=d(!0),V=d(""),c=d(""),g=d([]),f=d([]),B=d(!1),M=d(0),T=d(""),L=d(""),q=d(""),J=d(0),re=[{label:"UTF-8",value:"utf-8"},{label:"GBK",value:"gbk"},{label:"GB2312",value:"gb2312"},{label:"GB18030",value:"gb18030"},{label:"UTF-16",value:"utf-16"}],ue=[{label:"自动检测",value:"auto"},{label:"第X章",value:"chapter"},{label:"卷X",value:"volume"},{label:"自定义",value:"custom"}],Q=se(()=>!(h.value.length===0||_.value&&!V.value.trim()||!_.value&&!c.value));function A(o){const e=o.split(".").pop()?.toLowerCase();return e==="txt"?$e:e==="md"?He:e==="epub"?je:Xe}function n(o){return o<1024?o+" B":o<1024*1024?(o/1024).toFixed(1)+" KB":(o/(1024*1024)).toFixed(2)+" MB"}function F(o){const e=o.target;e.files&&(h.value=Array.from(e.files),K())}function R(o){$.value=!1,o.dataTransfer?.files&&(h.value=Array.from(o.dataTransfer.files).filter(e=>{const v=e.name.split(".").pop()?.toLowerCase();return["txt","md","epub"].includes(v||"")}),K())}function D(){h.value=[],y.value="",z.value="",f.value=[]}function Z(o){h.value.splice(o,1),h.value.length===0?(y.value="",z.value="",f.value=[]):z.value===h.value[o]?.name&&K()}async function K(){if(h.value.length===0)return;const o=h.value[0];z.value=o.name;try{const e=await oe(o);y.value=e.substring(0,2e3)+(e.length>2e3?"...":""),le(e)}catch{y.value="无法读取文件内容"}}function oe(o){return new Promise((e,v)=>{const a=new FileReader;a.onload=()=>e(a.result),a.onerror=v,a.readAsText(o,C.value)})}function le(o){const e=[],v=[/第[\u4e00-\u9fa5\d]+章[\s\S]*?(?=第[\u4e00-\u9fa5\d]+章|$)/g,/卷[\u4e00-\u9fa5\d]+[\s\S]*?(?=卷[\u4e00-\u9fa5\d]+|$)/g,/Chapter\s*\d+[\s\S]*?(?=Chapter\s*\d+|$)/gi,/第[\u4e00-\u9fa5\d]+节[\s\S]*?(?=第[\u4e00-\u9fa5\d]+节|$)/g];for(const a of v){let i;for(;(i=a.exec(o))!==null;){const b=i[0].split(`
`)[0].trim();b&&!e.some(S=>S.title===b)&&e.push({title:b,start:i.index,end:i.index+i[0].length})}}if(e.length===0){const a=o.split(`
`);let i="";a.forEach((b,S)=>{b.trim()===""&&i.trim()?(e.push({title:`第${e.length+1}章`,start:0,end:0}),i=""):i+=b+`
`}),i.trim()&&e.push({title:`第${e.length+1}章`,start:0,end:0})}f.value=e.slice(0,50)}function ce(){K()}async function de(){try{const o=await be.listBooks();g.value=o.books||[],g.value.length>0&&(c.value=g.value[0].id)}catch{g.value=[]}}async function N(){if(Q.value){B.value=!0,M.value=0,T.value="",L.value="正在处理文件...",J.value=0;try{const o=h.value[0],e=await oe(o);le(e),M.value=30,L.value="正在创建作品...";let v=c.value;if(_.value){const i=V.value.trim()||o.name.replace(/\.[^.]+$/,""),b="book-"+Date.now().toString(36)+Math.random().toString(36).substr(2,9),S=await be.createBook({book_id:b,title:i});v=S.book_id||S.id||b}M.value=50,L.value="正在导入内容...";const a=f.value.length||1;for(let i=0;i<a;i++){L.value=`正在导入第 ${i+1} / ${a} 章...`;let b="",S="";if(f.value[i]){const H=f.value[i];S=H.title;const Y=f.value[i+1];Y?b=e.substring(H.start,Y.start).trim():b=e.substring(H.start).trim()}else S=`第${i+1}章`,b=e;await be.rawRequest(`/books/${v}/chapters/${i+1}`,{method:"POST",body:JSON.stringify({title:S,content:b,number:i+1})}),J.value=i+1,M.value=50+Math.round((i+1)/a*45)}M.value=100,T.value="success",U.showToast(`成功导入 ${J.value} 个章节！`,"success")}catch(o){T.value="error",q.value=o.message||"未知错误",U.showToast(`导入失败: ${q.value}`,"error")}finally{B.value=!1}}}return Ae(()=>{de()}),(o,e)=>{const v=Je;return p(),m("div",et,[s("div",tt,[s("h2",at,[r(l(j),{size:"22",component:l(ye)},null,8,["component"]),e[8]||(e[8]=ee(" 导入中心 ",-1))]),e[9]||(e[9]=s("p",{class:"import-view__subtitle"},"从本地文件导入小说内容，支持多种格式",-1))]),s("div",st,[s("div",ot,[r(l(te),{bordered:!0,title:"选择文件",size:"small",class:"import-card"},{default:w(()=>[s("div",{class:Ke(["file-drop-zone",{"file-drop-zone--active":$.value}]),onDragover:e[0]||(e[0]=xe(a=>$.value=!0,["prevent"])),onDragleave:e[1]||(e[1]=a=>$.value=!1),onDrop:xe(R,["prevent"])},[s("input",{type:"file",accept:".txt,.md,.epub",class:"file-input",onChange:F,multiple:""},null,32),s("div",lt,[r(l(j),{size:48,component:l(Ee),class:"file-drop-zone__icon"},null,8,["component"]),e[10]||(e[10]=s("p",{class:"file-drop-zone__text"},"拖拽文件到此处",-1)),e[11]||(e[11]=s("p",{class:"file-drop-zone__hint"},"或点击选择文件",-1)),e[12]||(e[12]=s("p",{class:"file-drop-zone__formats"},"支持格式：TXT、MD、EPUB",-1))])],34),h.value.length>0?(p(),m("div",it,[r(l(Ge)),s("div",nt,[e[14]||(e[14]=s("span",null,"已选择文件",-1)),r(l(ie),{text:"",size:"small",onClick:D},{icon:w(()=>[r(l(j),{size:12},{default:w(()=>[r(l(ze))]),_:1})]),default:w(()=>[e[13]||(e[13]=ee(" 清空 ",-1))]),_:1})]),(p(!0),m(Ce,null,Se(h.value,(a,i)=>(p(),m("div",{key:i,class:"selected-file-item"},[r(l(j),{size:16,component:A(a.name)},null,8,["component"]),s("span",rt,x(a.name),1),s("span",ut,x(n(a.size)),1),r(l(ie),{text:"",size:"tiny",onClick:b=>Z(i)},{default:w(()=>[r(l(j),{size:12},{default:w(()=>[r(l(ze))]),_:1})]),_:1},8,["onClick"])]))),128))])):ne("",!0)]),_:1}),r(l(te),{bordered:!0,title:"导入选项",size:"small",class:"import-card"},{default:w(()=>[s("div",ct,[e[15]||(e[15]=s("span",{class:"config-label"},"文件编码",-1)),r(l(ge),{value:C.value,"onUpdate:value":e[2]||(e[2]=a=>C.value=a),options:re,size:"small",class:"config-select"},null,8,["value"])]),s("div",dt,[e[16]||(e[16]=s("span",{class:"config-label"},"章节分隔",-1)),r(l(ge),{value:I.value,"onUpdate:value":e[3]||(e[3]=a=>I.value=a),options:ue,size:"small",class:"config-select"},null,8,["value"])]),s("div",vt,[e[17]||(e[17]=s("span",{class:"config-label"},"自动检测标题",-1)),r(l(Be),{value:E.value,"onUpdate:value":e[4]||(e[4]=a=>E.value=a),size:"small"},null,8,["value"])]),s("div",ht,[e[18]||(e[18]=s("span",{class:"config-label"},"创建新作品",-1)),r(l(Be),{value:_.value,"onUpdate:value":e[5]||(e[5]=a=>_.value=a),size:"small"},null,8,["value"])]),_.value?(p(),m("div",ft,[e[19]||(e[19]=s("span",{class:"config-label"},"作品名称",-1)),r(v,{value:V.value,"onUpdate:value":e[6]||(e[6]=a=>V.value=a),placeholder:"输入作品名称",size:"small",class:"config-input"},null,8,["value"])])):(p(),m("div",pt,[e[20]||(e[20]=s("span",{class:"config-label"},"添加到",-1)),r(l(ge),{value:c.value,"onUpdate:value":e[7]||(e[7]=a=>c.value=a),options:g.value.map(a=>({label:a.title,value:a.id})),placeholder:"选择作品",size:"small",class:"config-select"},null,8,["value","options"])]))]),_:1})]),s("div",mt,[r(l(te),{bordered:!0,title:"内容预览",size:"small",class:"import-card"},{default:w(()=>[y.value?(p(),m("div",gt,[s("div",wt,[s("span",_t,x(z.value),1),r(l(ie),{text:"",size:"tiny",onClick:ce},{icon:w(()=>[r(l(j),{size:12},{default:w(()=>[r(l(Le))]),_:1})]),default:w(()=>[e[22]||(e[22]=ee(" 刷新预览 ",-1))]),_:1})]),s("div",kt,[s("pre",yt,x(y.value),1)])])):(p(),m("div",bt,[r(l(j),{size:32,component:l($e),class:"preview-empty__icon"},null,8,["component"]),e[21]||(e[21]=s("p",null,"选择文件后预览内容",-1))]))]),_:1}),r(l(te),{bordered:!0,title:"章节检测",size:"small",class:"import-card"},{default:w(()=>[f.value.length===0?(p(),m("div",xt,[...e[23]||(e[23]=[s("p",null,"未检测到章节，或未选择文件",-1)])])):(p(),m("div",zt,[s("div",Ct,[r(l(Ye),{type:"success",size:"small"},{default:w(()=>[ee("检测到 "+x(f.value.length)+" 个章节",1)]),_:1})]),s("div",St,[(p(!0),m(Ce,null,Se(f.value.slice(0,10),(a,i)=>(p(),m("div",{key:i,class:"chapter-item"},[s("span",$t,x(i+1),1),s("span",Bt,x(a.title),1)]))),128)),f.value.length>10?(p(),m("div",Ft," 还有 "+x(f.value.length-10)+" 个章节... ",1)):ne("",!0)])]))]),_:1}),r(l(te),{bordered:!0,title:"开始导入",size:"small",class:"import-card"},{default:w(()=>[B.value?(p(),m("div",Rt,[r(l(qe),{percentage:M.value,status:T.value==="error"?"error":T.value==="success"?"success":"default","indicator-placement":"inside"},null,8,["percentage","status"]),T.value==="success"?(p(),m("p",Nt," 导入完成！已创建 "+x(J.value)+" 个章节 ",1)):T.value==="error"?(p(),m("p",Vt," 导入失败："+x(q.value),1)):(p(),m("p",Tt,x(L.value),1))])):ne("",!0),r(l(ie),{type:"primary",size:"large",block:"",loading:B.value,disabled:!Q.value,onClick:N},{icon:w(()=>[r(l(j),{component:l(ye)},null,8,["component"])]),default:w(()=>[ee(" "+x(B.value?"导入中...":"开始导入"),1)]),_:1},8,["loading","disabled"]),l(W)?ne("",!0):(p(),m("p",Dt," 后端未连接，无法执行导入 "))]),_:1})])])])}}}),Jt=We(Ot,[["__scopeId","data-v-dae21817"]]);export{Jt as default};
