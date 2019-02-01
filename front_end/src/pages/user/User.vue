<template>
  <el-container>
    <el-header>
      <el-row>
        <el-col :span="4" :offset="1" class="logo">Hi&nbsp;~,&nbsp;{{username}}</el-col>
      </el-row>
    </el-header>
    <el-main>
      <el-row>
        <el-col :span="12"><ve-pie :data="total_info" :settings="total_chart_settings"></ve-pie></el-col>
        <el-col :span="12"><ve-line :data="detail_info"></ve-line></el-col>
      </el-row>
      <el-row>
        <el-table :data="total" border style="width: 100%">
        <el-table-column prop="id" label="id"></el-table-column>
        <el-table-column prop="username" label="username"></el-table-column>
        <el-table-column prop="is_admin" label="is_admin"></el-table-column>
        <el-table-column prop="quota" label="quota(MB)"></el-table-column>
        <el-table-column prop="total_upload" label="upload(MB)"></el-table-column>
        <el-table-column prop="total_download" label="download(MB)"></el-table-column>
        <el-table-column prop="used" label="used(MB)"></el-table-column>
        <el-table-column prop="online_time" label="online_time(min)"></el-table-column>
        </el-table>
      </el-row>
      <el-row type="flex" justify="center">
        <el-col :span="2"><div class="detail_title">Detail List</div></el-col>
      </el-row>
      <el-row>
        <el-table :data="detaillist" border style="width: 100%">
          <el-table-column property="host" label="host" :sortable="true"></el-table-column>
          <el-table-column property="bind_port" label="bind_port" :sortable="true"></el-table-column>
          <el-table-column property="login_time" label="login_time" :sortable="true"></el-table-column>
          <el-table-column property="logout_time" label="logout_time" :sortable="true"></el-table-column>
          <el-table-column property="online_time" label="online_time(min)" :sortable="true"></el-table-column>
          <el-table-column property="upload" label="upload(MB)" :sortable="true"></el-table-column>
          <el-table-column property="download" label="download(MB)" :sortable="true"></el-table-column>
          <el-table-column property="used" label="used(MB)" :sortable="true"></el-table-column>
        </el-table>
      </el-row>
    </el-main>
  </el-container>
</template>

<script>
export default {
  data() {
    this.total_chart_settings = {
      dataType: function (v) {
        return v + ' MB'
      }
    }
    return {
      username: this.$store.state.username,
      user_id: this.$store.state.id,
      total_info: {
        columns: ['key', 'value'],
        rows: [
          { 'key': 'upload', 'value': 1 },
          { 'key': 'download', 'value': 1 },
          { 'key': 'unused', 'value': 1 },
        ]
      },
      detail_info: {
        columns: ['online_time', 'upload', 'download', 'used'],
        rows: [],
      },
      total: [],
      detaillist: [],
    }
  },
  mounted() {
    this.loadTotal()
  },
  methods: {
    loadTotal() {
      let upload = this.total_info.rows[0]
      let download = this.total_info.rows[1]
      let unused = this.total_info.rows[2]
      let total = this.total
      this.axios({
        method: 'get',
        url: '/user?id=' + this.user_id,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Authorization': 'Bearer ' + this.$store.state.token,
        },
      })
      .then(response => {
        upload.value = response.data.total_upload
        download.value = response.data.total_download
        unused.value = response.data.quota - upload.value - download.value
        total.push(response.data)
        this.loadDetail()
      })
    },
    loadDetail() {
      let data = this.detail_info.rows
      let detaillist = this.detaillist
      this.axios({
        method: 'get',
        url: '/detail?id=' + this.user_id,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Authorization': 'Bearer ' + this.$store.state.token,
        }
      })
      .then(response => {
        let details = response.data.detail
        for (let i = 0; i < details.length; i++) {
          data.push({
            'online_time': details[i].login_time + '~' + details[i].logout_time,
            'upload': details[i].upload,
            'download': details[i].download,
            'used': details[i].used
          })
          detaillist.push(details[i])
        }
      })
    }
  }
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

  .el-main
    background-color: #E9EEF3
    color: #333
    border-radius: 20px

  .detail_title
    font-size: 25px
    margin-top : 20px
    margin-bottom : 10px
</style>
