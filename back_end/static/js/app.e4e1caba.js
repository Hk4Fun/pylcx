(function(t){function e(e){for(var o,r,n=e[0],i=e[1],u=e[2],c=0,m=[];c<n.length;c++)r=n[c],l[r]&&m.push(l[r][0]),l[r]=0;for(o in i)Object.prototype.hasOwnProperty.call(i,o)&&(t[o]=i[o]);d&&d(e);while(m.length)m.shift()();return s.push.apply(s,u||[]),a()}function a(){for(var t,e=0;e<s.length;e++){for(var a=s[e],o=!0,n=1;n<a.length;n++){var i=a[n];0!==l[i]&&(o=!1)}o&&(s.splice(e--,1),t=r(r.s=a[0]))}return t}var o={},l={app:0},s=[];function r(e){if(o[e])return o[e].exports;var a=o[e]={i:e,l:!1,exports:{}};return t[e].call(a.exports,a,a.exports,r),a.l=!0,a.exports}r.m=t,r.c=o,r.d=function(t,e,a){r.o(t,e)||Object.defineProperty(t,e,{enumerable:!0,get:a})},r.r=function(t){"undefined"!==typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(t,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(t,"__esModule",{value:!0})},r.t=function(t,e){if(1&e&&(t=r(t)),8&e)return t;if(4&e&&"object"===typeof t&&t&&t.__esModule)return t;var a=Object.create(null);if(r.r(a),Object.defineProperty(a,"default",{enumerable:!0,value:t}),2&e&&"string"!=typeof t)for(var o in t)r.d(a,o,function(e){return t[e]}.bind(null,o));return a},r.n=function(t){var e=t&&t.__esModule?function(){return t["default"]}:function(){return t};return r.d(e,"a",e),e},r.o=function(t,e){return Object.prototype.hasOwnProperty.call(t,e)},r.p="/";var n=window["webpackJsonp"]=window["webpackJsonp"]||[],i=n.push.bind(n);n.push=e,n=n.slice();for(var u=0;u<n.length;u++)e(n[u]);var d=i;s.push([0,"chunk-vendors"]),a()})({0:function(t,e,a){t.exports=a("56d7")},"56d7":function(t,e,a){"use strict";a.r(e);a("7f7f"),a("cadf"),a("551c"),a("097d");var o=a("2b0e"),l=function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{attrs:{id:"app"}},[a("transition",{attrs:{name:"fade"}},[a("router-view")],1)],1)},s=[],r=a("f499"),n=a.n(r),i=a("5176"),u=a.n(i),d={name:"App",created:function(){var t=this;sessionStorage.getItem("store")&&this.$store.replaceState(u()({},this.$store.state,JSON.parse(sessionStorage.getItem("store")))),window.addEventListener("beforeunload",function(){sessionStorage.setItem("store",n()(t.$store.state))})}},c=d,m=(a("7faf"),a("2877")),p=Object(m["a"])(c,l,s,!1,null,null,null);p.options.__file="App.vue";var f=p.exports,b=a("5c96"),_=a.n(b),h=a("bc3a"),g=a.n(h),v=a("a7fe"),w=a.n(v),y=a("b408"),k=a.n(y),x=a("8c4f"),U=function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"login-wrapper"},[a("el-row",{staticClass:"login-row",attrs:{type:"flex",justify:"center"}},[a("el-col",{staticClass:"login-box",attrs:{span:8}},[a("div",{staticClass:"login-form"},[a("el-row",{staticClass:"form-title",attrs:{type:"flex",justify:"center"}},[a("el-col",{attrs:{span:4}},[a("span",[t._v("pylcx")])])],1),a("el-form",{attrs:{model:t.login_form}},[a("el-form-item",[a("el-input",{attrs:{placeholder:"enter username",clearable:""},model:{value:t.login_form.username,callback:function(e){t.$set(t.login_form,"username",e)},expression:"login_form.username"}})],1),a("el-form-item",[a("el-input",{attrs:{placeholder:"enter password",clearable:"",type:"password"},model:{value:t.login_form.password,callback:function(e){t.$set(t.login_form,"password",e)},expression:"login_form.password"}})],1)],1),a("el-row",{attrs:{type:"flex",justify:"center"}},[a("el-button",{staticClass:"login-bt",class:{"animated bounce":t.animate_left},attrs:{round:""},on:{click:function(e){t.handleLogin("user")}},nativeOn:{mouseenter:function(e){t.animate_left=!0},mouseleave:function(e){t.animate_left=!1}}},[a("span",{staticClass:"login-bt-font"},[t._v("Login as user")])]),a("el-button",{staticClass:"login-bt",class:{"animated bounce":t.animate_right},attrs:{round:""},on:{click:function(e){t.handleLogin("admin")}},nativeOn:{mouseenter:function(e){t.animate_right=!0},mouseleave:function(e){t.animate_right=!1}}},[a("span",{staticClass:"login-bt-font"},[t._v("Login as admin")])])],1)],1)])],1)],1)},A=[],q=(a("28a5"),{data:function(){return{login_form:{username:"",password:""},animate_left:!1,animate_right:!1}},methods:{handleLogin:function(t){var e=this,a=this.login_form.username;this.axios({method:"post",url:"/auth",headers:{"Access-Control-Allow-Origin":"*"},data:{username:this.login_form.username,password:this.login_form.password,login_as:t}}).then(function(o){if(200===o.status){var l=o.data.access_token,s=JSON.parse(atob(l.split(".")[1])).user_id;e.$store.commit("store_info",{token:l,username:a,id:s}),e.$router.push(t)}}).catch(function(t){if(401===t.response.status){var a=t.response.data.exception,o=t.response.data.reasons.join(",");e.$message({showClose:!0,message:a+": "+o,type:"warning"})}})}}}),C=q,O=(a("b2b1"),Object(m["a"])(C,U,A,!1,null,"0a64e085",null));O.options.__file="Login.vue";var $=O.exports,B=function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("el-container",[a("el-header",[a("el-row",[a("el-col",{staticClass:"logo",attrs:{span:4,offset:1}},[t._v("pylcx")]),a("el-col",{attrs:{span:2,offset:6}},[a("el-button",{attrs:{type:"primary",round:""},on:{click:t.getOnlineUsers}},[t._v("online users :  "+t._s(t.online_users))])],1),a("el-col",{attrs:{span:2,offset:9}},[a("el-button",{attrs:{type:"success",icon:"el-icon-plus",circle:""},on:{click:function(e){t.dialogUserAdd=!0}}})],1),a("el-dialog",{attrs:{title:"Online users",visible:t.dialogOnlineUsers,width:"80%"},on:{"update:visible":function(e){t.dialogOnlineUsers=e},close:function(e){t.onlineUserlist=[]}}},[a("el-table",{attrs:{data:t.onlineUserlist,height:"300",border:""}},[a("el-table-column",{attrs:{property:"id",label:"id",sortable:!0}}),a("el-table-column",{attrs:{property:"username",label:"username",sortable:!0}}),a("el-table-column",{attrs:{property:"host",label:"host",sortable:!0}}),a("el-table-column",{attrs:{property:"bind_port",label:"bind_port",sortable:!0}}),a("el-table-column",{attrs:{property:"upload",label:"upload(MB)",sortable:!0}}),a("el-table-column",{attrs:{property:"download",label:"download(MB)",sortable:!0}}),a("el-table-column",{attrs:{property:"login_time",label:"login_time",sortable:!0}})],1)],1),a("el-dialog",{attrs:{title:"Add User",visible:t.dialogUserAdd},on:{"update:visible":function(e){t.dialogUserAdd=e}}},[a("el-form",{attrs:{model:t.add_user_form}},[a("el-form-item",{attrs:{label:"username"}},[a("el-input",{attrs:{placeholder:"enter username",clearable:""},model:{value:t.add_user_form.username,callback:function(e){t.$set(t.add_user_form,"username",e)},expression:"add_user_form.username"}})],1),a("el-form-item",{attrs:{label:"password"}},[a("el-input",{attrs:{placeholder:"enter password",clearable:"",type:"password"},model:{value:t.add_user_form.password,callback:function(e){t.$set(t.add_user_form,"password",e)},expression:"add_user_form.password"}})],1),a("el-form-item",{attrs:{label:"quota(MB)"}},[a("el-input",{attrs:{placeholder:"set quota",clearable:""},model:{value:t.add_user_form.quota,callback:function(e){t.$set(t.add_user_form,"quota",e)},expression:"add_user_form.quota"}})],1),a("el-form-item",{attrs:{label:"admin"}},[a("el-radio",{attrs:{label:"0",border:""},model:{value:t.add_user_form.is_admin,callback:function(e){t.$set(t.add_user_form,"is_admin",e)},expression:"add_user_form.is_admin"}},[t._v("False")]),a("el-radio",{attrs:{label:"1",border:""},model:{value:t.add_user_form.is_admin,callback:function(e){t.$set(t.add_user_form,"is_admin",e)},expression:"add_user_form.is_admin"}},[t._v("True")])],1)],1),a("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{attrs:{type:"info"},on:{click:function(e){t.dialogUserAdd=!1}}},[t._v("Cancle")]),a("el-button",{attrs:{type:"primary"},on:{click:t.add_user}},[t._v("Confirm")])],1)],1)],1)],1),a("el-main",[a("el-table",{staticStyle:{width:"100%"},attrs:{data:t.userlist,border:"",height:"550","row-class-name":t.is_admin_row}},[a("el-table-column",{attrs:{prop:"id",label:"id",sortable:!0}}),a("el-table-column",{attrs:{prop:"username",label:"username",sortable:!0}}),a("el-table-column",{attrs:{prop:"is_admin",label:"is_admin",sortable:!0}}),a("el-table-column",{attrs:{prop:"quota",label:"quota(MB)",sortable:!0}}),a("el-table-column",{attrs:{prop:"total_upload",label:"upload(MB)",sortable:!0}}),a("el-table-column",{attrs:{prop:"total_download",label:"download(MB)",sortable:!0}}),a("el-table-column",{attrs:{prop:"used",label:"used(MB)",sortable:!0}}),a("el-table-column",{attrs:{prop:"online_time",label:"online_time(min)",sortable:!0}}),a("el-table-column",{attrs:{label:"options"},scopedSlots:t._u([{key:"default",fn:function(e){return[a("el-button",{attrs:{type:"success",icon:"el-icon-more",size:"mini",circle:""},on:{click:function(a){t.handleDetail(e.$index,e.row)}}}),a("el-button",{attrs:{type:"primary",icon:"el-icon-edit",size:"mini",circle:""},on:{click:function(a){t.handleQuotaEdit(e.$index,e.row)}}}),a("el-button",{attrs:{type:"danger",icon:"el-icon-delete",size:"mini",circle:""},on:{click:function(a){t.handleDelete(e.$index,e.row)}}})]}}])})],1),a("el-dialog",{attrs:{title:"Details",visible:t.dialogUserDetails,width:"100%"},on:{"update:visible":function(e){t.dialogUserDetails=e},close:function(e){t.detaillist=[]}}},[a("el-table",{staticStyle:{width:"100%"},attrs:{data:t.detaillist,height:"300",border:""}},[a("el-table-column",{attrs:{property:"host",label:"host",sortable:!0}}),a("el-table-column",{attrs:{property:"bind_port",label:"bind_port",sortable:!0}}),a("el-table-column",{attrs:{property:"login_time",label:"login_time",sortable:!0}}),a("el-table-column",{attrs:{property:"logout_time",label:"logout_time",sortable:!0}}),a("el-table-column",{attrs:{property:"online_time",label:"online_time(min)",sortable:!0}}),a("el-table-column",{attrs:{property:"upload",label:"upload(MB)",sortable:!0}}),a("el-table-column",{attrs:{property:"download",label:"download(MB)",sortable:!0}}),a("el-table-column",{attrs:{property:"used",label:"used(MB)",sortable:!0}})],1)],1),a("el-dialog",{attrs:{title:"Delete",visible:t.dialogUserDelete,width:"30%"},on:{"update:visible":function(e){t.dialogUserDelete=e}}},[a("span",[t._v("Are you sure to delete this user? This will lose all the data about this user!")]),a("span",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{attrs:{type:"info"},on:{click:function(e){t.dialogUserDelete=!1}}},[t._v("Cancle")]),a("el-button",{attrs:{type:"danger"},on:{click:t.deleteUserConfirmed}},[t._v("Confirm")])],1)]),a("el-dialog",{attrs:{title:"Quota",visible:t.dialogEditQuota,width:"30%"},on:{"update:visible":function(e){t.dialogEditQuota=e}}},[a("el-form",{attrs:{model:t.quota_edit_form}},[a("el-form-item",{attrs:{label:"quota(MB)"}},[a("el-input",{attrs:{placeholder:"set quota",clearable:""},model:{value:t.quota_edit_form.quota,callback:function(e){t.$set(t.quota_edit_form,"quota",e)},expression:"quota_edit_form.quota"}})],1)],1),a("span",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{attrs:{type:"info"},on:{click:function(e){t.dialogEditQuota=!1}}},[t._v("Cancle")]),a("el-button",{attrs:{type:"primary"},on:{click:t.changeQuota}},[t._v("Confirm")])],1)],1)],1)],1)},M=[],D={data:function(){return{online_users:"0",userlist:[],detaillist:[],onlineUserlist:[],dialogUserDetails:!1,dialogUserAdd:!1,dialogUserDelete:!1,dialogEditQuota:!1,dialogOnlineUsers:!1,add_user_form:{username:"",password:"",quota:"",is_admin:"0"},quota_edit_form:{quota:""},deleteUserId:"",deleteRowIdx:"",quotaEditUserId:"",row:{}}},mounted:function(){var t=this;this.$options.sockets.onmessage=function(e){return t.online_users=e.data};var e=this.userlist;this.axios({method:"get",url:"/users",headers:{"Access-Control-Allow-Origin":"*",Authorization:"Bearer "+this.$store.state.token}}).then(function(t){for(var a=t.data.users,o=0;o<a.length;o++)e.push(a[o])})},methods:{is_admin_row:function(t){var e=t.row;t.rowIndex;return 1===e.is_admin?"admin-row":""},handleDetail:function(t,e){this.dialogUserDetails=!0;var a=this.detaillist;this.axios({method:"get",url:"/detail?id="+e.id,headers:{"Access-Control-Allow-Origin":"*",Authorization:"Bearer "+this.$store.state.token}}).then(function(t){for(var e=t.data.detail,o=0;o<e.length;o++)a.push(e[o])})},add_user:function(){var t=this,e=this.add_user_form.username.trim(),a=this.add_user_form.password.trim(),o=this.add_user_form.quota.trim(),l=this.add_user_form.is_admin.trim();this.axios({method:"post",url:"/user",headers:{"Access-Control-Allow-Origin":"*",Authorization:"Bearer "+this.$store.state.token},data:{username:e,password:a,quota:o,is_admin:l}}).then(function(e){return t.getUserInfo(e.data.id)})},getUserInfo:function(t){var e=this;this.axios({method:"get",url:"/user?id="+t,headers:{"Access-Control-Allow-Origin":"*",Authorization:"Bearer "+this.$store.state.token}}).then(function(t){return e.pushUser(t)})},pushUser:function(t){this.userlist.push(t.data),this.dialogUserAdd=!1,this.add_user_form.username="",this.add_user_form.password="",this.add_user_form.quota="",this.add_user_form.is_admin="0"},handleQuotaEdit:function(t,e){this.dialogEditQuota=!0,this.quota_edit_form.quota=e.quota,this.quotaEditUserId=e.id,this.row=e},changeQuota:function(){var t=this.quota_edit_form.quota,e=this.row;this.dialogEditQuota=!1,this.axios({method:"put",url:"/user?id="+this.quotaEditUserId,headers:{"Access-Control-Allow-Origin":"*",Authorization:"Bearer "+this.$store.state.token},data:{quota:t}}).then(function(){e.quota=t})},handleDelete:function(t,e){this.dialogUserDelete=!0,this.deleteRowIdx=t,this.deleteUserId=e.id},deleteUserConfirmed:function(){var t=this;this.dialogUserDelete=!1,this.axios({method:"delete",url:"/user?id="+this.deleteUserId,headers:{"Access-Control-Allow-Origin":"*",Authorization:"Bearer "+this.$store.state.token}}).then(function(){return t.userlist.splice(t.deleteRowIdx,1)})},getOnlineUsers:function(){this.dialogOnlineUsers=!0;var t=this.onlineUserlist;this.axios({method:"get",url:"/online",headers:{"Access-Control-Allow-Origin":"*",Authorization:"Bearer "+this.$store.state.token}}).then(function(e){for(var a=e.data.online_users,o=0;o<a.length;o++)t.push(a[o])})}}},j=D,S=(a("d631"),Object(m["a"])(j,B,M,!1,null,"5301cf43",null));S.options.__file="Admin.vue";var E=S.exports,I=function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("el-container",[a("el-header",[a("el-row",[a("el-col",{staticClass:"logo",attrs:{span:4,offset:1}},[t._v("Hi ~, "+t._s(t.username))])],1)],1),a("el-main",[a("el-row",[a("el-col",{attrs:{span:12}},[a("ve-pie",{attrs:{data:t.total_info,settings:t.total_chart_settings}})],1),a("el-col",{attrs:{span:12}},[a("ve-line",{attrs:{data:t.detail_info}})],1)],1),a("el-row",[a("el-table",{staticStyle:{width:"100%"},attrs:{data:t.total,border:""}},[a("el-table-column",{attrs:{prop:"id",label:"id"}}),a("el-table-column",{attrs:{prop:"username",label:"username"}}),a("el-table-column",{attrs:{prop:"is_admin",label:"is_admin"}}),a("el-table-column",{attrs:{prop:"quota",label:"quota(MB)"}}),a("el-table-column",{attrs:{prop:"total_upload",label:"upload(MB)"}}),a("el-table-column",{attrs:{prop:"total_download",label:"download(MB)"}}),a("el-table-column",{attrs:{prop:"used",label:"used(MB)"}}),a("el-table-column",{attrs:{prop:"online_time",label:"online_time(min)"}})],1)],1),a("el-row",{attrs:{type:"flex",justify:"center"}},[a("el-col",{attrs:{span:2}},[a("div",{staticClass:"detail_title"},[t._v("Detail List")])])],1),a("el-row",[a("el-table",{staticStyle:{width:"100%"},attrs:{data:t.detaillist,border:""}},[a("el-table-column",{attrs:{property:"host",label:"host",sortable:!0}}),a("el-table-column",{attrs:{property:"bind_port",label:"bind_port",sortable:!0}}),a("el-table-column",{attrs:{property:"login_time",label:"login_time",sortable:!0}}),a("el-table-column",{attrs:{property:"logout_time",label:"logout_time",sortable:!0}}),a("el-table-column",{attrs:{property:"online_time",label:"online_time(min)",sortable:!0}}),a("el-table-column",{attrs:{property:"upload",label:"upload(MB)",sortable:!0}}),a("el-table-column",{attrs:{property:"download",label:"download(MB)",sortable:!0}}),a("el-table-column",{attrs:{property:"used",label:"used(MB)",sortable:!0}})],1)],1)],1)],1)},z=[],Q={data:function(){return this.total_chart_settings={dataType:function(t){return t+" MB"}},{username:this.$store.state.username,user_id:this.$store.state.id,total_info:{columns:["key","value"],rows:[{key:"upload",value:1},{key:"download",value:1},{key:"unused",value:1}]},detail_info:{columns:["online_time","upload","download","used"],rows:[]},total:[],detaillist:[]}},mounted:function(){this.loadTotal()},methods:{loadTotal:function(){var t=this,e=this.total_info.rows[0],a=this.total_info.rows[1],o=this.total_info.rows[2],l=this.total;this.axios({method:"get",url:"/user?id="+this.user_id,headers:{"Access-Control-Allow-Origin":"*",Authorization:"Bearer "+this.$store.state.token}}).then(function(s){e.value=s.data.total_upload,a.value=s.data.total_download,o.value=s.data.quota-e.value-a.value,l.push(s.data),t.loadDetail()})},loadDetail:function(){var t=this.detail_info.rows,e=this.detaillist;this.axios({method:"get",url:"/detail?id="+this.user_id,headers:{"Access-Control-Allow-Origin":"*",Authorization:"Bearer "+this.$store.state.token}}).then(function(a){for(var o=a.data.detail,l=0;l<o.length;l++)t.push({online_time:o[l].login_time+"~"+o[l].logout_time,upload:o[l].upload,download:o[l].download,used:o[l].used}),e.push(o[l])})}}},L=Q,T=(a("db20"),Object(m["a"])(L,I,z,!1,null,"203787c2",null));T.options.__file="User.vue";var P=T.exports;o["default"].use(x["a"]);var J=new x["a"]({routes:[{path:"/login",name:"login",component:$},{path:"/admin",name:"admin",component:E},{path:"/user",name:"user",component:P},{path:"*",redirect:"/login"}]}),R=a("2f62");o["default"].use(R["a"]);var N=new R["a"].Store({state:{token:"",username:"",id:""},mutations:{store_info:function(t,e){t.token=e.token,t.username=e.username,t.id=e.id},delete_info:function(t){t.token="",t.username="",t.id=""}}}),F=a("c3da"),H=a.n(F),G=a("40ea"),K=a.n(G);a("0fae"),a("77ed");o["default"].config.productionTip=!1,o["default"].use(_.a),o["default"].use(w.a,g.a),o["default"].use(k.a,"ws://192.168.1.100:8000/online_users"),o["default"].component(H.a.name,H.a),o["default"].component(K.a.name,K.a),g.a.defaults.timeout=5e3,g.a.defaults.baseURL="http://192.168.1.100:8000",new o["default"]({router:J,store:N,render:function(t){return t(f)}}).$mount("#app")},"7faf":function(t,e,a){"use strict";var o=a("8fba"),l=a.n(o);l.a},"8fba":function(t,e,a){},b2b1:function(t,e,a){"use strict";var o=a("da2b"),l=a.n(o);l.a},c95b:function(t,e,a){},cc3e:function(t,e,a){},d631:function(t,e,a){"use strict";var o=a("c95b"),l=a.n(o);l.a},da2b:function(t,e,a){},db20:function(t,e,a){"use strict";var o=a("cc3e"),l=a.n(o);l.a}});
//# sourceMappingURL=app.e4e1caba.js.map