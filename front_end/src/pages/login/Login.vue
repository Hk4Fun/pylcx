<template>
  <div class="login-wrapper">
    <el-row type="flex" justify="center" class="login-row">
      <el-col :span="8" class="login-box">
        <div class="login-form">
          <el-row type="flex" justify="center" class="form-title">
            <el-col :span="4"><span>pylcx</span></el-col>
          </el-row>
          <el-form :model="login_form">
            <el-form-item>
              <el-input v-model="login_form.username" placeholder="enter username" clearable></el-input>
            </el-form-item>
            <el-form-item>
              <el-input v-model="login_form.password" placeholder="enter password" clearable type="password"></el-input>
            </el-form-item>
          </el-form>
          <el-row type="flex" justify="center">
            <el-button
            round
            :class="{'animated bounce':animate_left}"
            @mouseenter.native="animate_left = true"
            @mouseleave.native="animate_left = false"
            @click="handleLogin('user')"
            class="login-bt">
              <span class="login-bt-font">Login as user</span>
            </el-button>
            <el-button
            round
            :class="{'animated bounce':animate_right}"
            @mouseenter.native="animate_right = true"
            @mouseleave.native="animate_right = false"
            @click="handleLogin('admin')"
            class="login-bt">
              <span class="login-bt-font">Login as admin</span>
            </el-button>
          </el-row>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script>
export default {
  data() {
    return {
      login_form: {
        username: '',
        password: '',
      },
      animate_left: false,
      animate_right: false
    }
  },
  methods: {
    handleLogin(login_as) {
      let username = this.login_form.username
      this.axios({
        method: 'post',
        url: '/auth',
        headers: {
          'Access-Control-Allow-Origin': '*',
        },
        data: {
          username: this.login_form.username,
          password: this.login_form.password,
          login_as
        }
      })
      .then(response => {
        if (response.status === 200) {
          let token = response.data.access_token
          let id = JSON.parse(atob(token.split('.')[1])).user_id
          this.$store.commit('store_info', {token, username, id})
          this.$router.push(login_as)
        }
      })
      .catch(error => {
        if (error.response.status === 401) {
          let exception = error.response.data.exception
          let reasons = (error.response.data.reasons).join(',')
          this.$message({
            showClose: true,
            message: exception + ': ' + reasons,
            type: 'warning'
          })
        }
      })
    },
  }
}
</script>

<style lang="stylus" scoped>
  .login-wrapper
    height: 100%
    position: relative
    background : #e5e9f2
    border-radius : 20px

  .login-row
    transform: translate(0, -50%)
    position: absolute !i
    top: 50%

  .login-form
    padding : 20px

  .login-bt
    width :100%

  .login-box
    border-radius : 20px
    background-color : #99a9bf
    box-shadow: 10px 10px 5px #888888

  .form-title
    margin-bottom : 20px
    font-size : 30px
    color: #5362a2

  .el-input
    font-size : 17px

  .login-bt-font
    font-size : 20px
</style>
