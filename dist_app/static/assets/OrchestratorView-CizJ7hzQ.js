import{ad as E,ab as _,an as R,ac as w,ap as le,aq as ie,d as I,h as y,a7 as ce,av as de,ag as ae,bD as ue,a8 as pe,v as me,a1 as ve,ak as fe,a9 as he,T as ge,bf as be,o as d,c as m,a as t,I as _e,D as we,Y as xe,j as o,k as a,u as s,bE as ye,N as O,x as h,B as C,F as J,l as Y,t as g,p as Q,i as X,M as ke,z as Ce,A as $e,K as T,q as ze,s as Se,r as x,R as N,_ as Re}from"./index-wHqlCVHi.js";import{P as Oe}from"./PlayCircleOutlined-DdRekxE0.js";import{a as Te,S as Ne}from"./ShakeOutlined-B271Wr4g.js";import{C as ee}from"./CheckCircleOutlined-DQs9K-lN.js";import{R as Ie}from"./RestOutlined-BMJfru-Q.js";import{N as se}from"./Tag-CodsH--1.js";import{N as Pe}from"./Input-DkuEDZVa.js";import{N as De}from"./Progress-1OnFMlCy.js";import{N as te}from"./Space-Bw70gRrr.js";import"./Suffix-DzKYYMWH.js";import"./get-slot-Bk_rJcZu.js";const Be=E([_("list",`
 --n-merged-border-color: var(--n-border-color);
 --n-merged-color: var(--n-color);
 --n-merged-color-hover: var(--n-color-hover);
 margin: 0;
 font-size: var(--n-font-size);
 transition:
 background-color .3s var(--n-bezier),
 color .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 padding: 0;
 list-style-type: none;
 color: var(--n-text-color);
 background-color: var(--n-merged-color);
 `,[R("show-divider",[_("list-item",[E("&:not(:last-child)",[w("divider",`
 background-color: var(--n-merged-border-color);
 `)])])]),R("clickable",[_("list-item",`
 cursor: pointer;
 `)]),R("bordered",`
 border: 1px solid var(--n-merged-border-color);
 border-radius: var(--n-border-radius);
 `),R("hoverable",[_("list-item",`
 border-radius: var(--n-border-radius);
 `,[E("&:hover",`
 background-color: var(--n-merged-color-hover);
 `,[w("divider",`
 background-color: transparent;
 `)])])]),R("bordered, hoverable",[_("list-item",`
 padding: 12px 20px;
 `),w("header, footer",`
 padding: 12px 20px;
 `)]),w("header, footer",`
 padding: 12px 0;
 box-sizing: border-box;
 transition: border-color .3s var(--n-bezier);
 `,[E("&:not(:last-child)",`
 border-bottom: 1px solid var(--n-merged-border-color);
 `)]),_("list-item",`
 position: relative;
 padding: 12px 0; 
 box-sizing: border-box;
 display: flex;
 flex-wrap: nowrap;
 align-items: center;
 transition:
 background-color .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 `,[w("prefix",`
 margin-right: 20px;
 flex: 0;
 `),w("suffix",`
 margin-left: 20px;
 flex: 0;
 `),w("main",`
 flex: 1;
 `),w("divider",`
 height: 1px;
 position: absolute;
 bottom: 0;
 left: 0;
 right: 0;
 background-color: transparent;
 transition: background-color .3s var(--n-bezier);
 pointer-events: none;
 `)])]),le(_("list",`
 --n-merged-color-hover: var(--n-color-hover-modal);
 --n-merged-color: var(--n-color-modal);
 --n-merged-border-color: var(--n-border-color-modal);
 `)),ie(_("list",`
 --n-merged-color-hover: var(--n-color-hover-popover);
 --n-merged-color: var(--n-color-popover);
 --n-merged-border-color: var(--n-border-color-popover);
 `))]),Me=Object.assign(Object.assign({},ae.props),{size:{type:String,default:"medium"},bordered:Boolean,clickable:Boolean,hoverable:Boolean,showDivider:{type:Boolean,default:!0}}),ne=ve("n-list"),Le=I({name:"List",props:Me,slots:Object,setup(i){const{mergedClsPrefixRef:n,inlineThemeDisabled:c,mergedRtlRef:p}=ce(i),v=de("List",p,n),$=ae("List","-list",Be,ue,i,n);fe(ne,{showDividerRef:he(i,"showDivider"),mergedClsPrefixRef:n});const b=me(()=>{const{common:{cubicBezierEaseInOut:P},self:{fontSize:z,textColor:j,color:f,colorModal:D,colorPopover:B,borderColor:q,borderColorModal:A,borderColorPopover:M,borderRadius:K,colorHover:L,colorHoverModal:H,colorHoverPopover:W}}=$.value;return{"--n-font-size":z,"--n-bezier":P,"--n-text-color":j,"--n-color":f,"--n-border-radius":K,"--n-border-color":q,"--n-border-color-modal":A,"--n-border-color-popover":M,"--n-color-modal":D,"--n-color-popover":B,"--n-color-hover":L,"--n-color-hover-modal":H,"--n-color-hover-popover":W}}),u=c?pe("list",void 0,b,i):void 0;return{mergedClsPrefix:n,rtlEnabled:v,cssVars:c?void 0:b,themeClass:u?.themeClass,onRender:u?.onRender}},render(){var i;const{$slots:n,mergedClsPrefix:c,onRender:p}=this;return p?.(),y("ul",{class:[`${c}-list`,this.rtlEnabled&&`${c}-list--rtl`,this.bordered&&`${c}-list--bordered`,this.showDivider&&`${c}-list--show-divider`,this.hoverable&&`${c}-list--hoverable`,this.clickable&&`${c}-list--clickable`,this.themeClass],style:this.cssVars},n.header?y("div",{class:`${c}-list__header`},n.header()):null,(i=n.default)===null||i===void 0?void 0:i.call(n),n.footer?y("div",{class:`${c}-list__footer`},n.footer()):null)}}),Ve=I({name:"ListItem",slots:Object,setup(){const i=ge(ne,null);return i||be("list-item","`n-list-item` must be placed in `n-list`."),{showDivider:i.showDividerRef,mergedClsPrefix:i.mergedClsPrefixRef}},render(){const{$slots:i,mergedClsPrefix:n}=this;return y("li",{class:`${n}-list-item`},i.prefix?y("div",{class:`${n}-list-item__prefix`},i.prefix()):null,i.default?y("div",{class:`${n}-list-item__main`},i):null,i.suffix?y("div",{class:`${n}-list-item__suffix`},i.suffix()):null,this.showDivider&&y("div",{class:`${n}-list-item__divider`}))}}),Ee={xmlns:"http://www.w3.org/2000/svg","xmlns:xlink":"http://www.w3.org/1999/xlink",viewBox:"0 0 1024 1024"},je=t("path",{d:"M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448s448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372s372 166.6 372 372s-166.6 372-372 372z",fill:"currentColor"},null,-1),qe=t("path",{d:"M686.7 638.6L544.1 535.5V288c0-4.4-3.6-8-8-8H488c-4.4 0-8 3.6-8 8v275.4c0 2.6 1.2 5 3.3 6.5l165.4 120.6c3.6 2.6 8.6 1.8 11.2-1.7l28.6-39c2.6-3.7 1.8-8.7-1.8-11.2z",fill:"currentColor"},null,-1),Ae=[je,qe],oe=I({name:"ClockCircleOutlined",render:function(n,c){return d(),m("svg",Ee,Ae)}}),Ke={xmlns:"http://www.w3.org/2000/svg","xmlns:xlink":"http://www.w3.org/1999/xlink",viewBox:"0 0 1024 1024"},He=t("path",{d:"M603.3 327.5l-246 178a7.95 7.95 0 0 0 0 12.9l246 178c5.3 3.8 12.7 0 12.7-6.5V643c0-10.2-4.9-19.9-13.2-25.9L457.4 512l145.4-105.2c8.3-6 13.2-15.6 13.2-25.9V334c0-6.5-7.4-10.3-12.7-6.5z",fill:"currentColor"},null,-1),We=t("path",{d:"M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448s448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372s372 166.6 372 372s-166.6 372-372 372z",fill:"currentColor"},null,-1),Fe=[He,We],re=I({name:"LeftCircleOutlined",render:function(n,c){return d(),m("svg",Ke,Fe)}}),Ge={class:"orchestrator-view"},Ue={class:"header"},Je={class:"header-content"},Ye={class:"title-section"},Qe={class:"main-content"},Xe={class:"conversation-panel"},Ze={class:"examples-section"},es={class:"examples-tags"},ss={class:"conversation-list"},ts={class:"message-content"},os={class:"message-role"},rs={class:"message-text"},as={class:"message-time"},ns={key:1,class:"empty-state"},ls={class:"input-section"},is={class:"progress-panel"},cs={key:0,class:"current-task"},ds={class:"task-name"},us={key:1,class:"no-task"},ps={key:0,class:"steps-list"},ms={class:"step-info"},vs={class:"step-name"},fs={class:"step-message"},hs={key:1,class:"empty-steps"},gs={key:0,class:"approval-modal"},bs=I({__name:"OrchestratorView",setup(i){const n=_e(),c=x(""),p=x([]),v=x(!1),$=x(0),b=x(""),u=x([]),P=x(!1),z=x(null),j=["我想写一本玄幻小说，主角从废柴开始逆袭","构建一个东方玄幻世界观","设计三个主要角色","写第一章，主角获得奇遇","让节奏更快一些","检查质量","这本书怎么样了"];let f=null;function D(){f&&f.close();const l=window.location.protocol==="https:"?"wss:":"ws:",e=window.location.host;f=new WebSocket(`${l}//${e}/api/orchestrator/ws/${Date.now()}`),f.onmessage=r=>{const S=r.data;console.log("WebSocket message:",S);try{const[Z,V]=S.split(": ",2);if(V.includes("执行")){const F=V.replace("执行: ",""),k=u.value.find(G=>G.name===F);k&&(k.status="running",k.message="执行中...")}else if(V.includes("完成")){const F=V.replace("完成: ",""),k=u.value.find(U=>U.name===F);k&&(k.status="completed",k.message="已完成");const G=u.value.filter(U=>U.status==="completed").length;$.value=Math.round(G/u.value.length*100)}}catch(Z){console.error("WebSocket parse error:",Z)}},f.onclose=()=>{setTimeout(D,5e3)}}async function B(){if(!c.value.trim()||v.value)return;const l=c.value.trim();c.value="",p.value.push({role:"user",content:l,timestamp:new Date}),v.value=!0,b.value=l;try{const r=await N.rawRequest("/orchestrator/say",{method:"POST",body:JSON.stringify({instruction:l})});p.value.push({role:"assistant",content:r.message||"操作完成",timestamp:new Date}),n.showToast(r.message||"操作完成",r.success?"success":"error")}catch(e){p.value.push({role:"assistant",content:`错误: ${e.message||"未知错误"}`,timestamp:new Date}),n.showToast(`操作失败: ${e.message}`,"error")}finally{v.value=!1,b.value=""}}async function q(){v.value=!0,$.value=0,b.value="章节生成中...",u.value=[{id:"snapshot",name:"KG快照拍摄",status:"pending",message:""},{id:"society",name:"社会推演",status:"pending",message:""},{id:"architect",name:"架构师蓝图",status:"pending",message:""},{id:"writer",name:"Writer抽卡",status:"pending",message:""},{id:"auditor",name:"8门禁审计",status:"pending",message:""},{id:"style",name:"去AI味润色",status:"pending",message:""},{id:"kg_update",name:"知识图谱更新",status:"pending",message:""},{id:"publish",name:"章节发布",status:"pending",message:""}];try{const e=await N.rawRequest("/orchestrator/execute-chapter",{method:"POST",body:JSON.stringify({book_id:"default",chapter:1,mode:"gacha_parallel_3",auto_approve:!0})});n.showToast(e.message,e.success?"success":"error")}catch(l){n.showToast(`章节生成失败: ${l.message}`,"error")}finally{v.value=!1}}async function A(){try{const l=await N.rawRequest("/orchestrator/status",{method:"GET"});console.log("Status:",l)}catch(l){console.error("Fetch status error:",l)}}async function M(){try{const l=await N.rawRequest("/orchestrator/conversation",{method:"GET"});p.value=l.map(e=>({role:e.role,content:e.content,timestamp:new Date}))}catch(l){console.error("Fetch conversation error:",l)}}async function K(){try{await N.rawRequest("/orchestrator/reset",{method:"POST"}),p.value=[],u.value=[],$.value=0,n.showToast("创作系统已重置","success")}catch(l){n.showToast(`重置失败: ${l.message}`,"error")}}function L(l){P.value=!1,z.value=null,n.showToast(l?"已通过审批":"已拒绝",l?"success":"warning")}function H(l){switch(l){case"completed":return ee;case"running":return Ie;case"failed":return re;default:return oe}}function W(l){switch(l){case"completed":return"success";case"running":return"primary";case"failed":return"error";default:return"default"}}return we(()=>{D(),M()}),xe(()=>{f&&f.close()}),(l,e)=>(d(),m("div",Ge,[t("div",Ue,[t("div",Je,[t("div",Ye,[o(s(O),{size:32,class:"title-icon"},{default:a(()=>[o(s(ye))]),_:1}),e[3]||(e[3]=t("div",null,[t("h1",{class:"title"},"智能创作中心"),t("p",{class:"subtitle"},"用自然语言驱动你的创造力")],-1))]),o(s(C),{type:"primary",onClick:q,disabled:v.value},{icon:a(()=>[o(s(Oe))]),default:a(()=>[e[4]||(e[4]=h(" 一键生成章节 ",-1))]),_:1},8,["disabled"])])]),t("div",Qe,[t("div",Xe,[o(s(T),{title:"创作对话",class:"conversation-card"},{default:a(()=>[t("div",Ze,[e[5]||(e[5]=t("span",{class:"examples-label"},"试试这些指令：",-1)),t("div",es,[(d(),m(J,null,Y(j,r=>o(s(se),{key:r,closable:!1,class:"example-tag",onClick:S=>c.value=r},{default:a(()=>[h(g(r),1)]),_:2},1032,["onClick"])),64))])]),t("div",ss,[p.value.length>0?(d(),Q(s(Le),{key:0},{default:a(()=>[(d(!0),m(J,null,Y(p.value,(r,S)=>(d(),Q(s(Ve),{key:S,class:X(["message-item",r.role])},{prefix:a(()=>[o(s(O),{size:20},{default:a(()=>[o(s(ke))]),_:1})]),default:a(()=>[t("div",ts,[t("span",os,g(r.role==="user"?"你":"AI"),1),t("p",rs,g(r.content),1),t("span",as,g(r.timestamp.toLocaleTimeString()),1)])]),_:2},1032,["class"]))),128))]),_:1})):(d(),m("div",ns,[o(s(O),{size:48,class:"empty-icon"},{default:a(()=>[o(s(Te))]),_:1}),e[6]||(e[6]=t("p",null,"开始你的创作之旅吧！",-1)),e[7]||(e[7]=t("p",{class:"empty-hint"},"输入你想创作的内容，AI会自动帮你完成",-1))]))]),t("div",ls,[o(s(Pe),{value:c.value,"onUpdate:value":e[0]||(e[0]=r=>c.value=r),type:"textarea",placeholder:v.value?"AI正在处理...":"输入你的创作需求，例如：我想写一本玄幻小说",disabled:v.value,rows:3,class:"input-textarea",onKeyup:Ce($e(B,["ctrl"]),["enter"])},null,8,["value","placeholder","disabled","onKeyup"]),o(s(C),{type:"primary",onClick:B,disabled:!c.value.trim()||v.value,class:"send-btn"},{icon:a(()=>[o(s(Ne))]),default:a(()=>[e[8]||(e[8]=h(" 发送 ",-1))]),_:1},8,["disabled"])])]),_:1})]),t("div",is,[o(s(T),{title:"当前任务",class:"task-card"},{default:a(()=>[b.value?(d(),m("div",cs,[o(s(De),{percentage:$.value,"show-indicator":!0},null,8,["percentage"]),t("p",ds,g(b.value),1)])):(d(),m("div",us,[o(s(O),{size:32,class:"no-task-icon"},{default:a(()=>[o(s(oe))]),_:1}),e[9]||(e[9]=t("p",null,"暂无进行中的任务",-1)),e[10]||(e[10]=t("p",{class:"no-task-hint"},'输入指令或点击"一键生成章节"开始创作',-1))]))]),_:1}),o(s(T),{title:"任务流程",class:"steps-card"},{default:a(()=>[u.value.length>0?(d(),m("div",ps,[(d(!0),m(J,null,Y(u.value,r=>(d(),m("div",{key:r.id,class:X(["step-item",r.status])},[o(s(O),{size:20,class:X(`step-icon step-${r.status}`)},{default:a(()=>[(d(),Q(ze(H(r.status))))]),_:2},1032,["class"]),t("div",ms,[t("span",vs,g(r.name),1),t("span",fs,g(r.message),1)]),o(s(se),{type:W(r.status),round:!0,class:"step-status"},{default:a(()=>[h(g(r.status==="pending"?"等待":r.status==="running"?"执行中":r.status==="completed"?"完成":"失败"),1)]),_:2},1032,["type"])],2))),128))])):(d(),m("div",hs,[...e[11]||(e[11]=[t("p",null,"任务步骤将在这里显示",-1)])]))]),_:1}),o(s(T),{title:"快捷操作",class:"actions-card"},{default:a(()=>[o(s(te),{vertical:""},{default:a(()=>[o(s(C),{onClick:A,size:"small"},{default:a(()=>[...e[12]||(e[12]=[h(" 刷新状态 ",-1)])]),_:1}),o(s(C),{onClick:M,size:"small"},{default:a(()=>[...e[13]||(e[13]=[h(" 加载对话 ",-1)])]),_:1}),o(s(C),{onClick:K,size:"small",type:"warning"},{default:a(()=>[...e[14]||(e[14]=[h(" 重置系统 ",-1)])]),_:1})]),_:1})]),_:1})])]),P.value&&z.value?(d(),m("div",gs,[o(s(T),{class:"approval-card",title:"需要人工确认"},{default:a(()=>[t("p",null,"子任务「"+g(z.value.name)+"」需要你的确认才能继续执行。",1),o(s(te),{class:"approval-actions"},{default:a(()=>[o(s(C),{onClick:e[1]||(e[1]=r=>L(!0)),type:"primary"},{icon:a(()=>[o(s(ee))]),default:a(()=>[e[15]||(e[15]=h(" 通过 ",-1))]),_:1}),o(s(C),{onClick:e[2]||(e[2]=r=>L(!1)),type:"warning"},{icon:a(()=>[o(s(re))]),default:a(()=>[e[16]||(e[16]=h(" 拒绝 ",-1))]),_:1})]),_:1})]),_:1})])):Se("",!0)]))}}),Ts=Re(bs,[["__scopeId","data-v-c9c2d530"]]);export{Ts as default};
