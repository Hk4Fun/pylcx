<template>
  <el-container>
    <el-header>
      <el-row>
        <el-col :span="4" :offset="1" class="logo">pylcx</el-col>
        <el-col :span="2" :offset="6">
          <el-button type="primary" round @click="getOnlineUsers">online&nbsp;users&nbsp;:&nbsp;&nbsp;{{online_users}}</el-button>
        </el-col>
        <el-col :span="2" :offset="9">
          <el-button type="success" icon="el-icon-plus" circle @click="dialogUserAdd = true"></el-button>
        </el-col>
        <el-dialog title="Online users" :visible.sync="dialogOnlineUsers" @close="onlineUserlist = []" width="80%">
          <el-table :data="onlineUserlist" height="300" border>
            <el-table-column property="id" label="id" :sortable="true"></el-table-column>
            <el-table-column property="username" label="username" :sortable="true"></el-table-column>
            <el-table-column property="host" label="host" :sortable="true"></el-table-column>
            <el-table-column property="bind_port" label="bind_port" :sortable="true"></el-table-column>
            <el-table-column property="upload" label="upload(MB)" :sortable="true"></el-table-column>
            <el-table-column property="download" label="download(MB)" :sortable="true"></el-table-column>
            <el-table-column property="login_time" label="login_time" :sortable="true"></el-table-column>
          </el-table>
        </el-dialog>
        <el-dialog title="Add User" :visible.sync="dialogUserAdd">
          <el-form :model="add_user_form">
            <el-form-item label="username">
              <el-input v-model="add_user_form.username" placeholder="enter username" clearable></el-input>
            </el-form-item>
            <el-form-item label="password">
              <el-input v-model="add_user_form.password" placeholder="enter password" clearable type="password"></el-input>
            </el-form-item>
            <el-form-item label="quota(MB)">
              <el-input v-model="add_user_form.quota" placeholder="set quota" clearable></el-input>
            </el-form-item>
            <el-form-item label="admin">
              <el-radio v-model="add_user_form.is_admin" label="0" border>False</el-radio>
              <el-radio v-model="add_user_form.is_admin" label="1" border>True</el-radio>
            </el-form-item>
          </el-form>
          <div slot="footer" class="dialog-footer">
            <el-button type="info" @click="dialogUserAdd = false">Cancle</el-button>
            <el-button type="primary" @click="add_user">Confirm</el-button>
          </div>
        </el-dialog>
      </el-row>
    </el-header>
    <el-main>
      <el-table :data="userlist" border height="550" style="width: 100%" :row-class-name="is_admin_row">
        <el-table-column prop="id" label="id" :sortable="true"></el-table-column>
        <el-table-column prop="username" label="username" :sortable="true"></el-table-column>
        <el-table-column prop="is_admin" label="is_admin" :sortable="true"></el-table-column>
        <el-table-column prop="quota" label="quota(MB)" :sortable="true"></el-table-column>
        <el-table-column prop="total_upload" label="upload(MB)" :sortable="true"></el-table-column>
        <el-table-column prop="total_download" label="download(MB)" :sortable="true"></el-table-column>
        <el-table-column prop="used" label="used(MB)" :sortable="true"></el-table-column>
        <el-table-column prop="online_time" label="online_time(min)" :sortable="true"></el-table-column>
        <el-table-column label="options">
          <template slot-scope="scope">
            <el-button type="success" icon="el-icon-more" size="mini" @click="handleDetail(scope.$index, scope.row)"
              circle>
            </el-button>
            <el-button type="primary" icon="el-icon-edit" size="mini" @click="handleQuotaEdit(scope.$index, scope.row)"
              circle>
            </el-button>
            <el-button type="danger" icon="el-icon-delete" size="mini" @click="handleDelete(scope.$index, scope.row)"
              circle>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-dialog title="Details" :visible.sync="dialogUserDetails" width="100%" @close="detaillist = []">
        <el-table :data="detaillist" height="300" border style="width: 100%">
          <el-table-column property="host" label="host" :sortable="true"></el-table-column>
          <el-table-column property="bind_port" label="bind_port" :sortable="true"></el-table-column>
          <el-table-column property="login_time" label="login_time" :sortable="true"></el-table-column>
          <el-table-column property="logout_time" label="logout_time" :sortable="true"></el-table-column>
          <el-table-column property="online_time" label="online_time(min)" :sortable="true"></el-table-column>
          <el-table-column property="upload" label="upload(MB)" :sortable="true"></el-table-column>
          <el-table-column property="download" label="download(MB)" :sortable="true"></el-table-column>
          <el-table-column property="used" label="used(MB)" :sortable="true"></el-table-column>
        </el-table>
      </el-dialog>
      <el-dialog title="Delete" :visible.sync="dialogUserDelete" width="30%">
        <span>Are you sure to delete this user? This will lose all the data about this user!</span>
        <span slot="footer" class="dialog-footer">
          <el-button type="info" @click="dialogUserDelete = false">Cancle</el-button>
          <el-button type="danger" @click="deleteUserConfirmed">Confirm</el-button>
        </span>
      </el-dialog>
      <el-dialog title="Quota" :visible.sync="dialogEditQuota" width="30%">
        <el-form :model="quota_edit_form">
          <el-form-item label="quota(MB)">
            <el-input v-model="quota_edit_form.quota" placeholder="set quota" clearable></el-input>
          </el-form-item>
        </el-form>
        <span slot="footer" class="dialog-footer">
          <el-button type="info" @click="dialogEditQuota = false">Cancle</el-button>
          <el-button type="primary" @click="changeQuota">Confirm</el-button>
        </span>
      </el-dialog>
    </el-main>
  </el-container>
</template>

<script>
  export default {
    data() {
      return {
        online_users: '0',
        userlist: [],
        detaillist: [],
        onlineUserlist: [],
        dialogUserDetails: false,
        dialogUserAdd: false,
        dialogUserDelete: false,
        dialogEditQuota: false,
        dialogOnlineUsers: false,
        add_user_form: {
          username: '',
          password: '',
          quota: '',
          is_admin: "0"
        },
        quota_edit_form: {
          quota: ''
        },
        deleteUserId: '',
        deleteRowIdx: '',
        quotaEditUserId: '',
        row: {},
      }
    },
    mounted() {
      this.$options.sockets.onmessage = (msg) => this.online_users = msg.data
      let userlist = this.userlist;
      this.axios({
          method: 'get',
          url: '/users',
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Authorization': 'Bearer ' + this.$store.state.token,
          }
        })
        .then(response => {
          let users_data = response.data.users;
          for (let i = 0; i < users_data.length; i++) {
            userlist.push(users_data[i])
          }
        })
    },
    methods: {
      is_admin_row({
        row,
        rowIndex
      }) {
        if (row.is_admin === 1) {
          return 'admin-row'
        }
        return ''
      },

      handleDetail(idx, row) {
        this.dialogUserDetails = true
        let detaillist = this.detaillist
        this.axios({
            method: 'get',
            url: '/detail?id=' + row.id,
            headers: {
              'Access-Control-Allow-Origin': '*',
              'Authorization': 'Bearer ' + this.$store.state.token,
            }
          })
          .then(response => {
            let details = response.data.detail
            for (let i = 0; i < details.length; i++) {
              detaillist.push(details[i])
            }
          })
      },

      add_user() {
        let name = this.add_user_form.username.trim();
        let pwd = this.add_user_form.password.trim();
        let quota = this.add_user_form.quota.trim();
        let is_admin = this.add_user_form.is_admin.trim();
        this.axios({
          method: 'post',
          url: '/user',
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Authorization': 'Bearer ' + this.$store.state.token,
          },
          data: {
            username: name,
            password: pwd,
            quota: quota,
            is_admin: is_admin,
          }
        }).then(response => this.getUserInfo(response.data.id))
      },

      getUserInfo(user_id) {
        this.axios({
            method: 'get',
            url: '/user?id=' + user_id,
            headers: {
              'Access-Control-Allow-Origin': '*',
              'Authorization': 'Bearer ' + this.$store.state.token,
            },
          })
          .then(response => this.pushUser(response))
      },

      pushUser(response) {
        this.userlist.push(response.data)
        this.dialogUserAdd = false
        this.add_user_form.username = ''
        this.add_user_form.password = ''
        this.add_user_form.quota = ''
        this.add_user_form.is_admin = '0'
      },

      handleQuotaEdit(idx, row) {
        this.dialogEditQuota = true
        this.quota_edit_form.quota = row.quota
        this.quotaEditUserId = row.id
        this.row = row
      },

      changeQuota() {
        let quota = this.quota_edit_form.quota
        let row = this.row
        this.dialogEditQuota = false
        this.axios({
            method: 'put',
            url: '/user?id=' + this.quotaEditUserId,
            headers: {
              'Access-Control-Allow-Origin': '*',
              'Authorization': 'Bearer ' + this.$store.state.token,
            },
            data: {
              quota
            }

          })
          .then(() => {
            row.quota = quota
          })
      },

      handleDelete(idx, row) {
        this.dialogUserDelete = true
        this.deleteRowIdx = idx
        this.deleteUserId = row.id
      },

      deleteUserConfirmed() {
        this.dialogUserDelete = false
        this.axios({
            method: 'delete',
            url: '/user?id=' + this.deleteUserId,
            headers: {
              'Access-Control-Allow-Origin': '*',
              'Authorization': 'Bearer ' + this.$store.state.token,
            }
          })
          .then(() => this.userlist.splice(this.deleteRowIdx, 1))
      },

      getOnlineUsers() {
        this.dialogOnlineUsers = true
        let onlineUserlist = this.onlineUserlist
        this.axios({
            method: 'get',
            url: '/online',
            headers: {
              'Access-Control-Allow-Origin': '*',
              'Authorization': 'Bearer ' + this.$store.state.token,
            }
          })
          .then(response => {
            let users = response.data.online_users
            for (let i = 0; i < users.length; i++) {
              onlineUserlist.push(users[i])
            }
          })
      }
    },
  }

</script>

<style lang="stylus" scoped>
  .el-header
    background-color: #B3C0D1
    color: #333
    line-height: 55px
    border-radius: 20px

  .logo
    font-size: 40px

  .el-table .admin-row
    background: #c4d3e6

  .el-main
    background-color: #E9EEF3
    color: #333
    border-radius: 20px

  .el-table
    border-radius: 15px

</style>
