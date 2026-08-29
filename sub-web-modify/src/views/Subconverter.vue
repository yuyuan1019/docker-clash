<template>
  <div>
    <el-row class="sub-main-row">
      <el-col :xs="24" :sm="22" :md="22" :lg="20" :xl="16" class="sub-main-col">
        <el-card class="sub-card" shadow="hover">
          <div slot="header">
            <el-tag size="small" :type="mihomoStatusTag.type" style="float:left;cursor:pointer" @click="getMihomoStatus">
              <i class="el-icon-cpu"></i> {{ mihomoStatusTag.text }}
            </el-tag>
            <el-link type="primary" icon="el-icon-connection" style="float:right" :href="xdPanelUrl" target="_blank" rel="noopener noreferrer">打开面板</el-link>
            <div style="text-align:center;font-size:15px">订 阅 转 换</div>
          </div>
          <el-container>
            <el-form class="sub-form" :model="form" label-width="88px" label-position="left">
              <el-form-item label="订阅链接:">
                <el-row v-for="(item, index) in form.subLinks" :key="index" :gutter="8" class="sub-link-row">
                  <el-col :xs="24" :sm="8" class="sub-link-name">
                    <el-input v-model="item.name" placeholder="提供商名称/简称，如：A"/>
                  </el-col>
                  <el-col :xs="21" :sm="14">
                    <el-input v-model="item.url" placeholder="订阅链接或单节点链接"/>
                  </el-col>
                  <el-col :xs="3" :sm="2" style="text-align:center">
                    <el-button icon="el-icon-delete" circle size="mini" type="danger" plain class="sub-link-del" @click="removeSubLink(index)" :disabled="form.subLinks.length === 1"></el-button>
                  </el-col>
                </el-row>
                <el-button icon="el-icon-plus" size="small" style="width:100%" @click="addSubLink">添加订阅链接</el-button>
                <div class="sub-tip">每行一条订阅；提供商名称会用于 proxy-provider 和地区组后缀；同源多账号请填写唯一名称，节点会自动增加来源前缀</div>
              </el-form-item>
              <el-form-item label="生成类型:">
                <el-select v-model="form.clientType" style="width: 100%">
                  <el-option v-for="(v, k) in options.clientTypes" :key="k" :label="k" :value="v"></el-option>
                </el-select>
              </el-form-item>
              <el-form-item label="后端地址:">
                <el-select
                    v-model="form.customBackend"
                    allow-create
                    filterable
                    @change="selectChanged"
                    placeholder="可输入自己的后端"
                    style="width: 100%"
                >
                  <el-option v-for="(v, k) in options.customBackend" :key="k" :label="k" :value="v"></el-option>
                </el-select>
              </el-form-item>
              <el-form-item label="短链选择:">
                <el-select
                    v-model="form.shortType"
                    allow-create
                    filterable
                    placeholder="可输入其他可用短链API"
                    style="width: 100%"
                >
                  <el-option v-for="(v, k) in options.shortTypes" :key="k" :label="k" :value="v"></el-option>
                </el-select>
              </el-form-item>
              <el-form-item label="远程配置:">
                <el-select
                    v-model="form.remoteConfig"
                    allow-create
                    filterable
                    placeholder="请选择"
                    style="width: 100%"
                >
                  <el-option-group
                      v-for="group in options.remoteConfig"
                      :key="group.label"
                      :label="group.label"
                  >
                    <el-option
                        v-for="item in group.options"
                        :key="item.value"
                        :label="item.label"
                        :value="item.value"
                    ></el-option>
                  </el-option-group>
                </el-select>
              </el-form-item>
              <el-form-item class="advanced-section" label-width="0px">
                <el-collapse>
                  <el-collapse-item>
                    <template slot="title">
                      <el-form-item label="高级功能:" style="width: 100%;">
                        <el-button
                            type="limr"
                            style="width: 100%;"
                            icon="el-icon-more-outline"
                        >点击显示/隐藏
                        </el-button>
                      </el-form-item>
                    </template>
                    <el-form-item label="自定义UA:">
                      <el-input v-model="form.diyua" placeholder="设置后端获取订阅链接时所用的自定义User-Agent"/>
                    </el-form-item>
                    <el-form-item label="包含节点:">
                      <el-input v-model="form.includeRemarks" placeholder="要保留的节点，支持正则"/>
                    </el-form-item>
                    <el-form-item label="排除节点:">
                      <el-input v-model="form.excludeRemarks" placeholder="要排除的节点，支持正则"/>
                    </el-form-item>
                    <el-form-item label="更新间隔:">
                      <el-input v-model="form.interval" placeholder="订阅自动更新间隔，单位为天，默认 7 天"/>
                    </el-form-item>
                    <el-form-item label="订阅命名:">
                      <el-input v-model="form.filename" @input="onFilenameInput"
                                placeholder="留空自动填写：单订阅=提供商名，多订阅=合集"/>
                    </el-form-item>
                    <el-form-item class="eldiy" label-width="0px">
                      <el-row type="flex">
                        <el-col>
                          <el-checkbox v-model="form.nodeList" label="仅输出节点信息" border></el-checkbox>
                        </el-col>
                        <el-popover placement="bottom" v-model="form.extraset">
                          <el-row :gutter="10">
                            <el-col :span="12">
                              <el-checkbox v-model="form.emoji" label="Emoji"></el-checkbox>
                            </el-col>
                            <el-col :span="12">
                              <el-checkbox v-model="form.insert" label="插入默认节点"></el-checkbox>
                            </el-col>
                          </el-row>
                          <el-row :gutter="10">
                            <el-col :span="12">
                              <el-checkbox v-model="form.udp" label="启用 UDP"></el-checkbox>
                            </el-col>
                            <el-col :span="12">
                              <el-checkbox v-model="form.xudp" label="启用 XUDP"></el-checkbox>
                            </el-col>
                          </el-row>
                          <el-row :gutter="10">
                            <el-col :span="12">
                              <el-checkbox v-model="form.tfo" label="启用 TFO"></el-checkbox>
                            </el-col>
                            <el-col :span="12">
                              <el-checkbox v-model="form.sort" label="基础节点排序"></el-checkbox>
                            </el-col>
                          </el-row>
                          <el-row :gutter="10">
                            <el-col :span="12">
                              <el-checkbox v-model="form.tpl.clash.doh" label="Clash.DoH"></el-checkbox>
                            </el-col>
                            <el-col :span="12">
                              <el-checkbox v-model="form.appendType" label="插入节点类型"></el-checkbox>
                            </el-col>
                          </el-row>
                          <el-row :gutter="10">
                            <el-col :span="12">
                              <el-checkbox v-model="form.tpl.surge.doh" label="Surge.DoH"></el-checkbox>
                            </el-col>
                            <el-col :span="12">
                              <el-checkbox v-model="form.tls13" label="开启TLS_1.3"></el-checkbox>
                            </el-col>
                          </el-row>
                          <el-row :gutter="10">
                            <el-col :span="12">
                              <el-checkbox v-model="form.expand" label="展开规则全文"></el-checkbox>
                            </el-col>
                            <el-col :span="12">
                              <el-checkbox v-model="form.new_name" label="Clash新字段名"></el-checkbox>
                            </el-col>
                          </el-row>
                          <el-row :gutter="10">
                            <el-col :span="12">
                              <el-checkbox v-model="form.scv" label="跳过证书验证"></el-checkbox>
                            </el-col>
                            <el-col :span="12">
                              <el-checkbox v-model="form.fdn" label="过滤不支持节点"></el-checkbox>
                            </el-col>
                          </el-row>
                          <el-row :gutter="10">
                            <el-col :span="12">
                              <div style="margin-left: 35%">
                                <el-checkbox v-model="form.tpl.singbox.ipv6" label="Sing-Box支持IPV6"></el-checkbox>
                              </div>
                            </el-col>
                          </el-row>
                          <el-button slot="reference">更多选项</el-button>
                        </el-popover>
                      </el-row>
                    </el-form-item>
                  </el-collapse-item>
                </el-collapse>
              </el-form-item>
              <el-divider class="result-divider" content-position="center">
                <el-button
                    type="zhuti"
                    @click="change">
                  <i id="rijian" class="el-icon-sunny"></i>
                  <i id="yejian" class="el-icon-moon"></i>
                </el-button>
              </el-divider>
              <el-form-item class="result-field" label="定制订阅:">
                <el-input class="copy-content" disabled v-model="customSubUrl">
                  <el-button
                      slot="append"
                      v-clipboard:copy="customSubUrl"
                      v-clipboard:success="onCopy"
                      ref="copy-btn"
                      icon="el-icon-document-copy"
                  >复制
                  </el-button>
                </el-input>
              </el-form-item>
              <el-form-item class="result-field" label="订阅短链:">
                <el-input class="copy-content" v-model="customShortSubUrl"
                          placeholder="输入自定义短链接后缀，点击生成短链接可反复生成">
                  <el-button
                      slot="append"
                      v-clipboard:copy="customShortSubUrl"
                      v-clipboard:success="onCopy"
                      ref="copy-btn"
                      icon="el-icon-document-copy"
                  >复制
                  </el-button>
                </el-input>
              </el-form-item>
              <el-form-item class="action-group action-group-primary" label-width="0px">
                <el-button
                    style="width: 120px"
                    type="danger"
                    class="action-btn"
                    @click="makeUrl"
                    :disabled="sourceSubUrl.length === 0 || btnBoolean"
                >生成订阅链接
                </el-button>
                <el-button
                    style="width: 120px"
                    type="danger"
                    class="action-btn"
                    @click="makeShortUrl"
                    :loading="loading1"
                    :disabled="customSubUrl.length === 0"
                >生成短链接
                </el-button>
                <el-button
                    style="width: 140px"
                    type="warning"
                    class="action-btn"
                    icon="el-icon-cpu"
                    @click="generateLatestConfig"
                    :loading="applying"
                    :disabled="customSubUrl.length === 0"
                >生成最新配置
                </el-button>
                <el-button
                    style="width: 150px"
                    type="success"
                    class="action-btn"
                    icon="el-icon-refresh"
                    @click="activateLatestConfig"
                    :loading="switchingConfig"
                >切换当前配置
                </el-button>
                <el-button
                    style="width: 140px"
                    type="info"
                    class="action-btn"
                    icon="el-icon-switch-button"
                    @click="controlMihomo('stop')"
                    :loading="controlling"
                >关闭 mihomo
                </el-button>
              </el-form-item>
              <el-form-item class="action-group action-group-secondary" label-width="0px">
                <el-button
                    style="width: 120px"
                    type="primary"
                    class="action-btn"
                    @click="dialogUploadConfigVisible = true"
                    icon="el-icon-upload"
                    :loading="loading2"
                >自定义配置
                </el-button>
                <el-button
                    style="width: 120px"
                    type="primary"
                    class="action-btn"
                    @click="dialogLoadConfigVisible = true"
                    icon="el-icon-copy-document"
                    :loading="loading3"
                >从URL解析
                </el-button>
              </el-form-item>
              <el-form-item class="action-group action-group-import" label-width="0px">
                <el-button
                    style="width: 250px;"
                    type="success"
                    class="action-btn-wide"
                    icon="el-icon-download"
                    @click="importToClash"
                    :disabled="!canImportClash"
                >一键导入 Clash
                </el-button>
              </el-form-item>
            </el-form>
          </el-container>
        </el-card>
      </el-col>
    </el-row>
    <el-dialog
        :visible.sync="dialogUploadConfigVisible"
        :show-close="false"
        :close-on-click-modal="false"
        :close-on-press-escape="false"
        :width="isPC ? '80%' : '96%'"
    >
      <el-tabs v-model="activeName" type="card">
        <el-tab-pane label="远程配置上传" name="first">
          <el-link type="danger" :href="sampleConfig" style="margin-bottom: 15px" target="_blank" icon="el-icon-info">
            参考案例
          </el-link>
          <el-form label-position="left">
            <el-form-item prop="uploadConfig">
              <el-input
                  v-model="uploadConfig"
                  type="textarea"
                  :autosize="{ minRows: 15, maxRows: 15}"
                  maxlength="50000"
                  show-word-limit
              ></el-input>
            </el-form-item>
          </el-form>
          <div style="float: right">
            <el-button type="primary" @click="uploadConfig = ''; dialogUploadConfigVisible = false">取 消</el-button>
            <el-button
                type="primary"
                @click="confirmUploadConfig"
                :disabled="uploadConfig.length === 0"
            >确 定
            </el-button>
          </div>
        </el-tab-pane>
        <el-tab-pane label="JS排序节点" name="second">
          <el-link type="success" :href="scriptConfig" style="margin-bottom: 15px" target="_blank" icon="el-icon-info">
            参考案例
          </el-link>
          <el-form label-position="left">
            <el-form-item prop="uploadScript">
              <el-input
                  v-model="uploadScript"
                  placeholder="本功能暂停使用，如有兴趣，自行去我的GitHub参考sub-web-api项目部署！"
                  type="textarea"
                  :autosize="{ minRows: 15, maxRows: 15}"
                  maxlength="50000"
                  show-word-limit
              ></el-input>
            </el-form-item>
          </el-form>
          <div style="float: right">
            <el-button type="primary" @click="uploadScript = ''; dialogUploadConfigVisible = false">取 消</el-button>
            <el-button
                type="primary"
                @click="confirmUploadScript"
                :disabled="uploadScript.length === 0"
            >确 定
            </el-button>
          </div>
        </el-tab-pane>
        <el-tab-pane label="JS筛选节点" name="third">
          <el-link type="warning" :href="filterConfig" style="margin-bottom: 15px" target="_blank" icon="el-icon-info">
            参考案例
          </el-link>
          <el-form label-position="left">
            <el-form-item prop="uploadFilter">
              <el-input
                  v-model="uploadFilter"
                  placeholder="本功能暂停使用，如有兴趣，自行去我的GitHub参考sub-web-api项目部署！"
                  type="textarea"
                  :autosize="{ minRows: 15, maxRows: 15}"
                  maxlength="50000"
                  show-word-limit
              ></el-input>
            </el-form-item>
          </el-form>
          <div style="float: right">
            <el-button type="primary" @click="uploadFilter = ''; dialogUploadConfigVisible = false">取 消</el-button>
            <el-button
                type="primary"
                @click="confirmUploadScript"
                :disabled="uploadFilter.length === 0"
            >确 定
            </el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
    <el-dialog
        :visible.sync="dialogLoadConfigVisible"
        :show-close="false"
        :close-on-click-modal="false"
        :close-on-press-escape="false"
        :width="isPC ? '80%' : '96%'"
    >
      <div slot="title">
        可以从生成的长/短链接中解析信息,填入页面中去
      </div>
      <el-form label-position="left">
        <el-form-item prop="uploadConfig">
          <el-input
              v-model="loadConfig"
              type="textarea"
              :autosize="{ minRows: 15, maxRows: 15}"
              maxlength="5000"
              show-word-limit
          ></el-input>
        </el-form-item>
      </el-form>
      <div slot="footer" class="dialog-footer">
        <el-button type="primary" @click="loadConfig = ''; dialogLoadConfigVisible = false">取 消</el-button>
        <el-button
            type="primary"
            @click="confirmLoadConfig"
            :disabled="loadConfig.length === 0"
        >确 定
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>
<script>
const project = process.env.VUE_APP_PROJECT
const configScriptBackend = process.env.VUE_APP_CONFIG_UPLOAD_BACKEND + '/api.php'
const remoteConfigSample = process.env.VUE_APP_SUBCONVERTER_REMOTE_CONFIG
const scriptConfigSample = process.env.VUE_APP_SCRIPT_CONFIG
const filterConfigSample = process.env.VUE_APP_FILTER_CONFIG
const defaultBackend = process.env.VUE_APP_SUBCONVERTER_DEFAULT_BACKEND
const shortUrlBackend = process.env.VUE_APP_MYURLS_DEFAULT_BACKEND + '/short'
// ===== 本站动态地址（根据当前访问域名自动生成，不写死 127.0.0.1 或固定域名）=====
// 部署后 nginx 将 /subapi/ 反代到 SubConverter 后端，/short 反代到 zurl 短链 API
const siteOrigin = window.location.origin
const localBackend = siteOrigin + '/subapi'
const localProviderRegionBackend = siteOrigin + '/provider-regions'
const localShort = siteOrigin + '/short'
const customClashConfigBase = 'https://github.com/Aethersailor/Custom_OpenClash_Rules/raw/main/cfg/'
const customClashUrl = name => customClashConfigBase + name
const providerRegionConfigPrefix = 'provider-regions:'
const builtInConfigModes = [
  {
    prefix: providerRegionConfigPrefix,
    backend: localProviderRegionBackend,
    clashOnlyMessage: '香港/日本提供商复写版仅支持 Clash 生成类型'
  }
]

function resolveBuiltInConfigMode(remoteConfig) {
  return builtInConfigModes.find(mode => remoteConfig.startsWith(mode.prefix))
}

function stripBuiltInConfigPrefix(remoteConfig) {
  const mode = resolveBuiltInConfigMode(remoteConfig)
  return mode ? remoteConfig.slice(mode.prefix.length) : remoteConfig
}
const customClashVariants = [
  {
    file: 'Custom_Clash.ini',
    label: 'Custom_Clash（默认推荐）',
    providerLabel: 'Custom_Clash（香港/日本按提供商细分）'
  },
  {
    file: 'Custom_Clash_Full.ini',
    label: 'Custom_Clash_Full（GitHub 原版）',
    providerLabel: 'Custom_Clash_Full（香港/日本按提供商细分）'
  },
  {
    file: 'Custom_Clash_Lite.ini',
    label: 'Custom_Clash_Lite（精简）',
    providerLabel: 'Custom_Clash_Lite（香港/日本按提供商细分）'
  },
  {
    file: 'Custom_Clash_GFW.ini',
    label: 'Custom_Clash_GFW（仅GFW名单）',
    providerLabel: 'Custom_Clash_GFW（香港/日本按提供商细分）'
  },
  {
    file: 'Custom_Clash_Mainland.ini',
    label: 'Custom_Clash_Mainland（回国）',
    providerLabel: 'Custom_Clash_Mainland（香港/日本按提供商细分）'
  },
  {
    file: 'Custom_Clash_Fallback.ini',
    label: 'Custom_Clash_Fallback（故障转移）',
    providerLabel: 'Custom_Clash_Fallback（香港/日本按提供商细分）'
  },
  {
    file: 'Custom_Clash_Full_Fallback.ini',
    label: 'Custom_Clash_Full_Fallback（全规则+故障转移）',
    providerLabel: 'Custom_Clash_Full_Fallback（香港/日本按提供商细分）'
  },
  {
    file: 'Custom_Clash_Lite_Fallback.ini',
    label: 'Custom_Clash_Lite_Fallback（精简+故障转移）',
    providerLabel: 'Custom_Clash_Lite_Fallback（香港/日本按提供商细分）'
  },
  {
    file: 'Custom_Clash_GFW_Fallback.ini',
    label: 'Custom_Clash_GFW_Fallback（GFW+故障转移）',
    providerLabel: 'Custom_Clash_GFW_Fallback（香港/日本按提供商细分）'
  }
]

function buildCustomClashOptions() {
  return customClashVariants.reduce((options, variant) => {
    const configUrl = customClashUrl(variant.file)
    options.push({
      label: variant.label,
      value: configUrl
    })
    options.push({
      label: variant.providerLabel,
      value: providerRegionConfigPrefix + configUrl
    })
    return options
  }, [])
}
const configUploadBackend = process.env.VUE_APP_CONFIG_UPLOAD_BACKEND + '/sub.php'
const tgBotLink = process.env.VUE_APP_BOT_LINK
const yglink = process.env.VUE_APP_YOUTUBE_LINK
const bzlink = process.env.VUE_APP_BILIBILI_LINK
export default {
  data() {
    return {
      backendVersion: "",
      activeName: 'first',
      // 是否为 PC 端
      isPC: true,
      btnBoolean: false,
      options: {
        clientTypes: {
          Clash: "clash",
          ShadowRocket: "shadowrocket",
          "Surge4/5": "surge&ver=4",
          "Sing-Box": "singbox",
          V2Ray: "v2ray",
          Trojan: "trojan",
          ShadowsocksR: "ssr",
          "混合订阅（mixed）": "mixed",
          Surfboard: "surfboard",
          Quantumult: "quan",
          "Quantumult X": "quanx",
          Loon: "loon",
          Mellow: "mellow",
          Surge3: "surge&ver=3",
          Surge2: "surge&ver=2",
          ClashR: "clashr",
          "Shadowsocks(SIP002)": "ss",
          "Shadowsocks Android(SIP008)": "sssub",
          ShadowsocksD: "ssd",
          "自动判断客户端": "auto",
        },
        shortTypes: {
          "本站短链(zurl)": localShort,
        },
        customBackend: {
          "本站后端(SubConverter)": localBackend,
        },
        backendOptions: [
          {value: localBackend},
        ],
        remoteConfig: [
          {
            label: "Custom_Clash（OpenClash/mihomo）",
            options: buildCustomClashOptions()
          }
        ]
      },
      form: {
        subLinks: [{ name: "", url: "" }],
        clientType: "",
        customBackend: this.getUrlParam() == "" ? localBackend : this.getUrlParam(),
        shortType: localShort,
        remoteConfig: "https://github.com/Aethersailor/Custom_OpenClash_Rules/raw/main/cfg/Custom_Clash.ini",
        excludeRemarks: "官网|余额|欠费|剩余|套餐|失效|网络优化|年付|更新",
        includeRemarks: "",
        filename: "",
        rename: "",
        devid: "",
        interval: "7",
        diyua: "clash-verge/v2.4.5",
        emoji: true,
        nodeList: false,
        extraset: false,
        tls13: false,
        udp: true,
        xudp: true,
        tfo: false,
        sort: false,
        expand: true,
        scv: true,
        fdn: false,
        appendType: false,
        insert: false, // 是否插入默认订阅的节点，对应配置项 insert_url
        new_name: true, // 是否使用 Clash 新字段
        tpl: {
          surge: {
            doh: false // dns 查询是否使用 DoH
          },
          clash: {
            doh: false
          },
          singbox: {
            ipv6: false
          }
        }
      },
      loading1: false,
      // 生成最新候选配置按钮加载状态
      applying: false,
      // 将最新候选配置切换为当前 config.yaml 的按钮状态
      switchingConfig: false,
      // 关闭/启动 mihomo 按钮加载状态
      controlling: false,
      // mihomo 运行状态：true=运行中 false=已停止 null=未知
      mihomoStatus: null,
      statusTimer: null,
      // 订阅命名是否自动管理（用户手动修改后关闭，清空后恢复自动）
      filenameAuto: true,
      formPersistenceReady: false,
      formSaveTimer: null,
      loading2: false,
      loading3: false,
      customSubUrl: "",
      customShortSubUrl: "",
      // 记录短链对应的长链，避免修改配置后误导入旧短链。
      shortUrlSource: "",
      dialogUploadConfigVisible: false,
      loadConfig: "",
      dialogLoadConfigVisible: false,
      uploadFilter: "",
      uploadScript: "",
      uploadConfig: "",
      myBot: tgBotLink,
      filterConfig: filterConfigSample,
      scriptConfig: scriptConfigSample,
      sampleConfig: remoteConfigSample,
      // 面板与本站同源部署；直接链接不依赖异步接口，浏览器可稳定打开新标签页。
      xdPanelUrl: window.location.origin + "/xd/"
    };
  },
  computed: {
    // 将「提供商+链接」行拼接为 SubConverter-Extended 支持的 tag/provider 前缀格式
    sourceSubUrl() {
      return this.form.subLinks
        .map(r => {
          const name = (r.name || "").trim().replace(/[,|<>]/g, "");
          const url = (r.url || "").trim();
          if (url === "") return "";
          if (name === "") return url;
          // http(s) 订阅用 provider: 命名代理提供者；单节点链接用 tag: 命名节点
          return (/^https?:\/\//i.test(url) ? "provider:" : "tag:") + name + "," + url;
        })
        .filter(s => s !== "")
        .join("|");
    },
    mihomoStatusTag() {
      if (this.mihomoStatus === true) return { text: "mihomo 运行中", type: "success" };
      if (this.mihomoStatus === false) return { text: "mihomo 已停止", type: "info" };
      return { text: "mihomo 状态未知", type: "danger" };
    },
    canImportClash() {
      return this.customSubUrl !== "" && this.form.clientType.startsWith("clash");
    }
  },
  watch: {
    form: {
      deep: true,
      handler() {
        this.queueServerFormSave();
      }
    },
    // 订阅链接行变化时自动推导订阅命名：单订阅=提供商名，两条及以上=合集
    "form.subLinks": {
      deep: true,
      handler() {
        this.autoFilename();
      }
    }
  },
  created() {
    document.title = "在线订阅转换工具";
    this.isPC = this.$getOS().isPc;
  },
  beforeDestroy() {
    if (this.statusTimer) {
      clearInterval(this.statusTimer);
      this.statusTimer = null;
    }
    if (this.formSaveTimer) {
      clearTimeout(this.formSaveTimer);
      this.formSaveTimer = null;
    }
  },
  mounted() {
    this.form.clientType = "clash";
    this.loadServerForm().finally(() => {
      this.formPersistenceReady = true;
      this.getBackendVersion();
    });
    this.getMihomoStatus();
    this.statusTimer = setInterval(this.getMihomoStatus, 30000);
    this.anhei();
    let lightMedia = window.matchMedia('(prefers-color-scheme: light)');
    let darkMedia = window.matchMedia('(prefers-color-scheme: dark)');
    let callback = (e) => {
      if (e.matches) {
        this.anhei();
      }
    };
    if (typeof darkMedia.addEventListener === 'function' || typeof lightMedia.addEventListener === 'function') {
      lightMedia.addEventListener('change', callback);
      darkMedia.addEventListener('change', callback);
    } //监听系统主题，自动切换！
  },
  methods: {
    applySavedForm(saved) {
      if (!saved || saved.version !== 1 || !saved.form || typeof saved.form !== "object") return;
      Object.keys(this.form).forEach(key => {
        if (key === "subLinks") {
          if (!Array.isArray(saved.form.subLinks)) return;
          const rows = saved.form.subLinks
              .slice(0, 50)
              .filter(row => row && typeof row === "object")
              .map(row => ({
                name: typeof row.name === "string" ? row.name : "",
                url: typeof row.url === "string" ? row.url : ""
              }));
          this.form.subLinks = rows.length ? rows : [{ name: "", url: "" }];
          return;
        }
        if (key === "tpl") {
          if (!saved.form.tpl || typeof saved.form.tpl !== "object") return;
          Object.keys(this.form.tpl).forEach(section => {
            const savedSection = saved.form.tpl[section];
            if (!savedSection || typeof savedSection !== "object") return;
            Object.keys(this.form.tpl[section]).forEach(option => {
              if (typeof savedSection[option] === typeof this.form.tpl[section][option]) {
                this.form.tpl[section][option] = savedSection[option];
              }
            });
          });
          return;
        }
        if (typeof saved.form[key] === typeof this.form[key]) {
          this.form[key] = saved.form[key];
        }
      });
      if (typeof saved.filenameAuto === "boolean") {
        this.filenameAuto = saved.filenameAuto;
      }
    },
    loadServerForm() {
      return this.$axios
          .get("/gateway/form-config", { timeout: 10000 })
          .then(res => {
            if (res.data.Code === 1 && res.data.FormConfig) {
              this.applySavedForm(res.data.FormConfig);
            }
          })
          .catch(() => {
            // 读取失败时继续使用页面默认值，不影响订阅转换。
          });
    },
    queueServerFormSave() {
      if (!this.formPersistenceReady) return;
      if (this.formSaveTimer) clearTimeout(this.formSaveTimer);
      this.formSaveTimer = setTimeout(() => {
        this.formSaveTimer = null;
        this.saveFormToServer();
      }, 500);
    },
    saveFormToServer() {
      return this.$axios
          .post("/gateway/form-config", {
          version: 1,
          form: this.form,
          filenameAuto: this.filenameAuto
          }, { timeout: 10000 })
          .catch(() => {
            // 自动保存失败不打断当前操作，下次修改时会再次尝试。
          });
    },
    selectChanged() {
      this.getBackendVersion();
    },
    addSubLink() {
      this.form.subLinks.push({ name: "", url: "" });
    },
    removeSubLink(index) {
      if (this.form.subLinks.length > 1) {
        this.form.subLinks.splice(index, 1);
      }
    },
    // 把生成/解析出的 url 参数（可能含 provider:/tag: 前缀）还原为行数据
    parseSubLinks(urlStr) {
      const rows = (urlStr || "").split("|").map(item => {
        let link = item.trim();
        let name = "";
        if (link.startsWith("<") && link.endsWith(">")) {
          link = link.slice(1, -1).trim();
        }
        const m = link.match(/^(?:provider|tag):([^,]*),(.*)$/i);
        if (m) {
          name = m[1].trim();
          link = m[2].trim();
        }
        return { name, url: link };
      }).filter(r => r.url !== "");
      this.form.subLinks = rows.length > 0 ? rows : [{ name: "", url: "" }];
    },
    autoFilename() {
      if (!this.filenameAuto) return;
      const valid = this.form.subLinks.filter(r => (r.url || "").trim() !== "");
      if (valid.length === 1) {
        this.form.filename = (valid[0].name || "").trim().replace(/[,|<>]/g, "");
      } else if (valid.length >= 2) {
        this.form.filename = "合集";
      } else {
        this.form.filename = "";
      }
    },
    onFilenameInput() {
      // 手动修改后不再自动覆盖；清空输入框则恢复自动命名
      this.filenameAuto = this.form.filename === "";
    },
    getUrlParam() {
      let query = window.location.search.substring(1);
      let vars = query.split('&');
      for (let i = 0; i < vars.length; i++) {
        var pair = vars[i].split('=');
        if (pair[0] == "backend") {
          return decodeURIComponent(pair[1]);
        }
      }
      return "";
    },
    anhei() {
      const getLocalTheme = window.localStorage.getItem("localTheme");
      const lightMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)');
      const darkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
      if (getLocalTheme) {
        document.getElementsByTagName('body')[0].className = getLocalTheme;
      } //读取localstorage，优先级最高！
      else if (getLocalTheme == null || getLocalTheme == "undefined" || getLocalTheme == "") {
        if (new Date().getHours() >= 19 || new Date().getHours() < 7) {
          document.getElementsByTagName('body')[0].setAttribute('class', 'dark-mode');
        } else {
          document.getElementsByTagName('body')[0].setAttribute('class', 'light-mode');
        } //根据当前时间来判断，用来对付QQ等不支持媒体变量查询的浏览器
        if (lightMode && lightMode.matches) {
          document.getElementsByTagName('body')[0].setAttribute('class', 'light-mode');
        }
        if (darkMode && darkMode.matches) {
          document.getElementsByTagName('body')[0].setAttribute('class', 'dark-mode');
        } //根据窗口主题来判断当前主题！
      }
    },
    change() {
      var zhuti = document.getElementsByTagName('body')[0].className;
      if (zhuti === 'light-mode') {
        document.getElementsByTagName('body')[0].setAttribute('class', 'dark-mode');
        window.localStorage.setItem('localTheme', 'dark-mode');
      }
      if (zhuti === 'dark-mode') {
        document.getElementsByTagName('body')[0].setAttribute('class', 'light-mode');
        window.localStorage.setItem('localTheme', 'light-mode');
      }
    },
    tanchuang() {
      this.$alert(`<div style="color:black;text-align:center;font-size:15px"><strong><span style="font-size:20px">本站官方TG交流群：</span><span><a href="https://t.me/feiyangdigital" target="_blank" style="color:red;font-size:20px;text-decoration:none">点击加入</a></span></strong></br><strong><span style="font-size:20px">老牌高端机场Rancho（<span style="color:blue">拥有数十不同国家节点，全部原生解锁支持奈飞、迪士尼、HBO等各种流媒体，全部套餐节点支持Chat GPT等各种AI，支持ISP住宅IP助力Tiktok等跨境贸易使用，采用最新Vless Encryption量子加密协议和AnyTLS双协议，在众多机场不稳定的今天，依旧生龙活虎，Vless Encryption量子加密协议和AnyTLS双协议+企业级跨境专线，是当下恶劣环境的最优解，全部套餐购买后直接赠送Emby影音服务，最高可体验4K杜比视界画展，媲美奈飞4K杜比视界，免费给购买了任意套餐的用户开放，稳定运营五年未跑路，在今年大多数机场纷纷倒闭的情况下，依旧坚挺扩张，还推出了包括Android TV在内的一键客户端，方便电视用户遥控操作，非常便利，强烈推荐，非常值得购买！</span>：<span><a href="https://www.mcwy.org" target="_blank" style="color:red;font-size:20px;text-decoration:none">点击注册</a></span></strong></br><strong><span style="font-size:20px">115蓝光4K原盘内部资源群</span></strong>）：</span><strong><span><a href="https://readme.115vip.shop/" target="_blank" style="color:red;font-size:20px;text-decoration:none">点击查看</a></span></strong></br><strong><span style="font-size:20px">奈飞、ChatGPT合租（<span style="color:blue">优惠码：feiyang</span>）：</span><span><a href="https://hezu.v1.mk/" style="color:red;font-size:20px;text-decoration:none">点击上车</a></span></strong></br>本站服务器赞助机场-牧场物语，BGP中继+IEPL企业级内网专线的高端机场，适合各个价位要求的用户，牧场物语采用最新的奈飞非自制剧解决方案，出口随机更换IP，确保尽可能的每个用户可以用上独立IP，以此来稳定解决奈飞非自制剧的封锁，并推出7*24小时奈飞非自制剧节点自动检测系统，用户再也不用自己手动一个个的乱试节点了，目前牧场的新加坡，台湾等节区域点均可做到24H稳定非自制剧观看，支持Chat-GPT和ISP住宅IP助力Tiktok等跨境贸易使用！</br></div>`, '信息面板', {
        confirmButtonText: '确定',
        dangerouslyUseHTMLString: true,
        customClass: 'msgbox'
      });
    },
    onCopy() {
      this.$message.success("已复制");
    },
    goToProject() {
      window.open(project);
    },
    gotoTgChannel() {
      window.open(tgBotLink);
    },
    gotoBiliBili() {
      window.open(bzlink);
    },
    gotoYouTuBe() {
      window.open(yglink);
    },
    importToClash() {
      if (!this.canImportClash) {
        this.$message.error("请先生成 Clash 订阅链接");
        return;
      }
      const shortUrl = this.customShortSubUrl.trim();
      const subscriptionUrl = /^https?:\/\//i.test(shortUrl) &&
          this.shortUrlSource === this.customSubUrl
          ? shortUrl
          : this.customSubUrl;
      window.location.href = "clash://install-config?url=" +
          encodeURIComponent(subscriptionUrl);
    },
    makeUrl() {
      if (this.sourceSubUrl === "" || this.form.clientType === "") {
        this.$message.error("订阅链接与客户端为必填项");
        return false;
      }
      let backend =
          this.form.customBackend === ""
              ? localBackend
              : this.form.customBackend;
      let remoteConfig = this.form.remoteConfig;
      const builtInMode = resolveBuiltInConfigMode(remoteConfig);
      if (builtInMode) {
        if (this.form.clientType !== "clash") {
          this.$message.error(builtInMode.clashOnlyMessage);
          return false;
        }
        backend = builtInMode.backend;
        remoteConfig = remoteConfig.slice(builtInMode.prefix.length);
      }
      let sourceSub = this.sourceSubUrl;
      this.customSubUrl =
          backend +
          "/sub?target=" +
          this.form.clientType +
          "&url=" +
          encodeURIComponent(sourceSub) +
          "&insert=" +
          this.form.insert;
      if (remoteConfig !== "") {
        this.customSubUrl +=
            "&config=" + encodeURIComponent(remoteConfig);
      }
      if (this.form.excludeRemarks !== "") {
        this.customSubUrl +=
            "&exclude=" + encodeURIComponent(this.form.excludeRemarks);
      }
      if (this.form.includeRemarks !== "") {
        this.customSubUrl +=
            "&include=" + encodeURIComponent(this.form.includeRemarks);
      }
      if (this.form.filename !== "") {
        this.customSubUrl +=
            "&filename=" + encodeURIComponent(this.form.filename);
      }
      if (this.form.rename !== "") {
        this.customSubUrl +=
            "&rename=" + encodeURIComponent(this.form.rename);
      }
      if (this.form.interval !== "") {
        this.customSubUrl +=
            "&interval=" + encodeURIComponent(this.form.interval * 86400);
      }
      if (this.form.devid !== "") {
        this.customSubUrl +=
            "&dev_id=" + encodeURIComponent(this.form.devid);
      }
      if (this.form.appendType) {
        this.customSubUrl +=
            "&append_type=" + this.form.appendType.toString();
      }
      if (this.form.tls13) {
        this.customSubUrl +=
            "&tls13=" + this.form.tls13.toString();
      }
      if (this.form.sort) {
        this.customSubUrl +=
            "&sort=" + this.form.sort.toString();
      }
      this.customSubUrl +=
          "&emoji=" +
          this.form.emoji.toString() +
          "&list=" +
          this.form.nodeList.toString() +
          "&xudp=" +
          this.form.xudp.toString() +
          "&udp=" +
          this.form.udp.toString() +
          "&tfo=" +
          this.form.tfo.toString() +
          "&expand=" +
          this.form.expand.toString() +
          "&scv=" +
          this.form.scv.toString() +
          "&fdn=" +
          this.form.fdn.toString();    
      if (this.form.clientType.includes("surge")) {
        if (this.form.tpl.surge.doh === true) {
          this.customSubUrl += "&surge.doh=true";
        }
      }
      if (this.form.clientType === "clash") {
        if (this.form.tpl.clash.doh === true) {
          this.customSubUrl += "&clash.doh=true";
        }
        this.customSubUrl += "&new_name=" + this.form.new_name.toString();
      }
      if (this.form.clientType === "singbox") {
        if (this.form.tpl.singbox.ipv6 === true) {
          this.customSubUrl += "&singbox.ipv6=1";
        }
      }
      if (this.form.diyua.trim() !== "") {
        this.customSubUrl +=
            "&diyua=" + encodeURIComponent(this.form.diyua);
      }
      this.$copyText(this.customSubUrl);
      this.$message.success("定制订阅已复制到剪贴板");
    },
    makeShortUrl() {
      let duan =
          this.form.shortType === ""
              ? localShort
              : this.form.shortType;
      this.loading1 = true;
      let data = new FormData();
      data.append("longUrl", this.$btoa(this.customSubUrl));
      if (this.customShortSubUrl.trim() != "") {
        data.append("shortKey", this.customShortSubUrl.trim().indexOf("http") < 0 ? this.customShortSubUrl.trim() : "");
      }
      this.$axios
          .post(duan, data, {
            header: {
              "Content-Type": "application/form-data; charset=utf-8"
            }
          })
          .then(res => {
            if (res.data.Code === 1 && res.data.ShortUrl !== "") {
              this.customShortSubUrl = res.data.ShortUrl;
              this.shortUrlSource = this.customSubUrl;
              this.$copyText(res.data.ShortUrl);
              this.$message.success("短链接已复制到剪贴板（IOS设备和Safari浏览器不支持自动复制API，需手动点击复制按钮）");
            } else {
              this.$message.error("短链接获取失败：" + res.data.Message);
            }
          })
          .catch(() => {
            this.$message.error("短链接获取失败");
          })
          .finally(() => {
            this.loading1 = false;
          });
    },
    generateLatestConfig() {
      this.applying = true;
      let data = new FormData();
      data.append("subUrl", this.customSubUrl);
      this.$axios
          .post("/apply", data, { timeout: 200000 })
          .then(res => {
            if (res.data.Code === 1) {
              this.$message.success(res.data.Message);
            } else {
              this.$message.error("生成失败：" + res.data.Message);
            }
          })
          .catch(() => {
            this.$message.error("生成请求失败，请检查网络或稍后再试");
          })
          .finally(() => {
            this.applying = false;
          });
    },
    activateLatestConfig() {
      this.switchingConfig = true;
      this.$axios
          .post("/mihomo/latest-config", null, { timeout: 60000 })
          .then(res => {
            if (res.data.Code === 1) {
              this.$message.success(res.data.Message);
            } else {
              this.$message.error("切换失败：" + res.data.Message);
            }
            this.getMihomoStatus();
          })
          .catch(() => {
            this.$message.error("切换请求失败，请检查 mihomo 状态或稍后再试");
          })
          .finally(() => {
            this.switchingConfig = false;
          });
    },
    getMihomoStatus() {
      this.$axios
          .get("/mihomo/status", { timeout: 10000 })
          .then(res => {
            if (res.data.Code === 1) {
              this.mihomoStatus = res.data.Running;
            } else {
              this.mihomoStatus = null;
            }
          })
          .catch(() => {
            this.mihomoStatus = null;
          });
    },
    controlMihomo(action) {
      const doPost = () => {
        this.controlling = true;
        this.$axios
            .post("/mihomo/" + action, null, { timeout: 60000 })
            .then(res => {
              if (res.data.Code === 1) {
                this.$message.success(res.data.Message);
              } else {
                this.$message.error("操作失败：" + res.data.Message);
              }
              this.getMihomoStatus();
            })
            .catch(() => {
              this.$message.error("操作请求失败，请检查网络或稍后再试");
            })
            .finally(() => {
              this.controlling = false;
            });
      };
      if (action === "stop") {
        this.$confirm("确定要关闭 mihomo 吗？代理服务将停止工作，面板也会断开连接。", "提示", {
          confirmButtonText: "确定关闭",
          cancelButtonText: "取消",
          type: "warning"
        }).then(doPost).catch(() => {});
      } else {
        doPost();
      }
    },
    confirmUploadConfig() {
      this.loading2 = true;
      let data = new FormData();
      data.append("config", encodeURIComponent(this.uploadConfig));
      this.$axios
          .post(configUploadBackend, data, {
            header: {
              "Content-Type": "application/form-data; charset=utf-8"
            }
          })
          .then(res => {
            if (res.data.code === 0 && res.data.data !== "") {
              this.$message.success(
                  "远程配置上传成功，配置链接已复制到剪贴板"
              );
              this.form.remoteConfig = res.data.data;
              this.$copyText(this.form.remoteConfig);
              this.dialogUploadConfigVisible = false;
            } else {
              this.$message.error("远程配置上传失败: " + res.data.msg);
            }
          })
          .catch(() => {
            this.$message.error("远程配置上传失败");
          })
          .finally(() => {
            this.loading2 = false;
          });
    },
    analyzeUrl() {
      if (this.loadConfig.indexOf("target") !== -1) {
        return this.loadConfig;
      } else {
        this.loading3 = true;
        return (async () => {
          try {
            let response = await fetch(this.loadConfig, {
              method: "GET",
              redirect: "follow",
            });
            return response.url;
          } catch (e) {
            this.$message.error("解析短链接失败，请检查短链接服务端是否配置跨域：" + e)
          } finally {
            this.loading3 = false;
          }
        })();
      }
    },
    confirmLoadConfig() {
      if (this.loadConfig.trim() === "" || !this.loadConfig.trim().includes("http")) {
        this.$message.error("待解析的订阅链接不合法");
        return false;
      }
      (async () => {
        let url
        try {
          url = new URL(await this.analyzeUrl())
        } catch (error) {
          this.$message.error("请输入正确的订阅地址!");
          return;
        }
        const parsedBackend = url.origin + url.pathname.replace(/\/sub$/, "");
        const builtInMode = builtInConfigModes.find(mode => mode.backend === parsedBackend);
        this.form.customBackend = builtInMode ? localBackend : parsedBackend;
        let param = new URLSearchParams(url.search);
        if (param.get("target")) {
          let target = param.get("target");
          if (target === 'surge' && param.get("ver")) {
            // 类型为surge,有ver
            this.form.clientType = target + "&ver=" + param.get("ver");
          } else if (target === 'surge') {
            //类型为surge,没有ver
            this.form.clientType = target + "&ver=4"
          } else {
            //类型为其他
            this.form.clientType = target;
          }
        }
        if (param.get("url")) {
          this.parseSubLinks(param.get("url"));
        }
        if (param.get("insert")) {
          this.form.insert = param.get("insert") === 'true';
        }
        if (param.get("config")) {
          this.form.remoteConfig = builtInMode
              ? builtInMode.prefix + param.get("config")
              : param.get("config");
        }
        if (param.get("exclude")) {
          this.form.excludeRemarks = param.get("exclude");
        }
        if (param.get("include")) {
          this.form.includeRemarks = param.get("include");
        }
        if (param.get("filename")) {
          this.form.filename = param.get("filename");
          this.filenameAuto = false;
        }
        if (param.get("rename")) {
          this.form.rename = param.get("rename");
        }
        if (param.get("interval")) {
          this.form.interval = Math.ceil(param.get("interval") / 86400);
        }
        if (param.get("dev_id")) {
          this.form.devid = param.get("dev_id");
        }
        if (param.get("append_type")) {
          this.form.appendType = param.get("append_type") === 'true';
        }
        if (param.get("tls13")) {
          this.form.tls13 = param.get("tls13");
        }
        if (param.get("xudp")) {
          this.form.xudp = param.get("xudp") === 'true';
        }
        if (param.get("sort")) {
          this.form.sort = param.get("sort") === 'true';
        }
        if (param.get("emoji")) {
          this.form.emoji = param.get("emoji") === 'true';
        }
        if (param.get("list")) {
          this.form.nodeList = param.get("list") === 'true';
        }
        if (param.get("udp")) {
          this.form.udp = param.get("udp") === 'true';
        }
        if (param.get("tfo")) {
          this.form.tfo = param.get("tfo") === 'true';
        }
        if (param.get("expand")) {
          this.form.expand = param.get("expand") === 'true';
        }
        if (param.get("scv")) {
          this.form.scv = param.get("scv") === 'true';
        }
        if (param.get("fdn")) {
          this.form.fdn = param.get("fdn") === 'true';
        }
        if (param.get("surge.doh")) {
          this.form.tpl.surge.doh = param.get("surge.doh") === 'true';
        }
        if (param.get("clash.doh")) {
          this.form.tpl.clash.doh = param.get("clash.doh") === 'true';
        }
        if (param.get("new_name")) {
          this.form.new_name = param.get("new_name") === 'true';
        }
        if (param.get("singbox.ipv6")) {
          this.form.tpl.singbox.ipv6 = param.get("singbox.ipv6") === '1';
        }
        if (param.get("diyua")) {
          this.form.diyua = param.get("diyua");
        }
        this.dialogLoadConfigVisible = false;
        this.$message.success("长/短链接已成功解析为订阅信息");
      })();
    },
    renderPost() {
      let data = new FormData();
      const remoteConfig = stripBuiltInConfigPrefix(this.form.remoteConfig);
      data.append("target", encodeURIComponent(this.form.clientType));
      data.append("url", encodeURIComponent(this.sourceSubUrl));
      data.append("config", encodeURIComponent(remoteConfig));
      data.append("exclude", encodeURIComponent(this.form.excludeRemarks));
      data.append("include", encodeURIComponent(this.form.includeRemarks));
      data.append("rename", encodeURIComponent(this.form.rename));
      data.append("tls13", encodeURIComponent(this.form.tls13.toString()));
      data.append("xudp", encodeURIComponent(this.form.xudp.toString()));
      data.append("emoji", encodeURIComponent(this.form.emoji.toString()));
      data.append("list", encodeURIComponent(this.form.nodeList.toString()));
      data.append("udp", encodeURIComponent(this.form.udp.toString()));
      data.append("tfo", encodeURIComponent(this.form.tfo.toString()));
      data.append("expand", encodeURIComponent(this.form.expand.toString()));
      data.append("scv", encodeURIComponent(this.form.scv.toString()));
      data.append("fdn", encodeURIComponent(this.form.fdn.toString()));
      data.append("sdoh", encodeURIComponent(this.form.tpl.surge.doh.toString()));
      data.append("cdoh", encodeURIComponent(this.form.tpl.clash.doh.toString()));
      data.append("newname", encodeURIComponent(this.form.new_name.toString()));
      data.append("diyua", encodeURIComponent(this.form.diyua.toString()));
      return data;
    },
    confirmUploadScript() {
      if (this.sourceSubUrl === "") {
        this.$message.error("订阅链接不能为空");
        return false;
      }
      this.loading2 = true;
      let data = this.renderPost();
      data.append("sortscript", encodeURIComponent(this.uploadScript));
      data.append("filterscript", encodeURIComponent(this.uploadFilter));
      this.$axios
          .post(configScriptBackend, data, {
            header: {
              "Content-Type": "application/form-data; charset=utf-8"
            }
          })
          .then(res => {
            if (res.data.code === 0 && res.data.data !== "") {
              this.$message.success(
                  "自定义JS上传成功，订阅链接已复制到剪贴板（IOS设备和Safari浏览器不支持自动复制API，需手动点击复制按钮）"
              );
              this.customSubUrl = res.data.data;
              this.$copyText(res.data.data);
              this.dialogUploadConfigVisible = false;
              this.btnBoolean = true;
            } else {
              this.$message.error("自定义JS上传失败: " + res.data.msg);
            }
          })
          .catch(() => {
            this.$message.error("自定义JS上传失败");
          })
          .finally(() => {
            this.loading2 = false;
          })
    },
    getBackendVersion() {
      this.$axios
          .get(
              this.form.customBackend + "/version"
          )
          .then(res => {
            this.backendVersion = res.data.replace(/backend\n$/gm, "");
            this.backendVersion = this.backendVersion.replace("subconverter", "SubConverter");
            this.$message.success(`${this.backendVersion}` + "后端连接成功，可以正常使用！");
          })
          .catch(() => {
            this.$message.error("请求SubConverter版本号返回数据失败，该后端不可用！");
          });
    }
  }
};
</script>

<style>
/* ===== docker-clash 定制：页面美化与响应式间距（不影响明暗主题配色）===== */
#app .sub-main-row.el-row:not(.el-row--flex) {
  margin-top: 0 !important;
  max-width: none;
  padding: 18px clamp(20px, 4vw, 64px) 42px !important;
}
/* el-col 默认 float:left，改为不浮动 + 自动外边距实现稳定居中 */
.sub-main-row > .sub-main-col {
  float: none;
  width: 100% !important;
  margin: 0 auto;
  max-width: 1480px;
}
.sub-card {
  border-radius: 14px;
}
.sub-card > .el-card__header {
  padding: 17px 24px;
}
.sub-card > .el-card__body {
  padding: 28px 32px 32px;
}
.sub-form {
  width: 100%;
}
.sub-form > .el-form-item {
  margin-bottom: 26px;
}
.sub-form > .el-form-item > .el-form-item__label {
  font-weight: 600;
}
.advanced-section {
  margin-top: 2px;
  margin-bottom: 36px !important;
}
#app .sub-card .sub-link-row.el-row:not(.el-row--flex) {
  max-width: none;
  margin: 0 0 12px !important;
  padding: 0 !important;
}
.sub-link-del {
  margin-top: 4px;
}
.sub-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
  margin-top: 8px;
}
.result-divider {
  margin: 42px 0 34px;
}
.result-field {
  margin-bottom: 24px !important;
}
.action-group {
  margin-bottom: 16px !important;
}
.action-group > .el-form-item__content {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 12px 14px;
  line-height: normal;
}
.action-group .el-button + .el-button {
  margin-left: 0;
}
.action-group-primary {
  margin-top: 42px;
}
.action-group-secondary {
  margin-top: 4px;
}
.action-group-import {
  margin-top: 6px;
}

/* 移动端适配 */
@media (max-width: 767px) {
  #app .sub-main-row.el-row:not(.el-row--flex) {
    padding: 0 4px 20px !important;
    margin-top: 4px !important;
  }
  .sub-card {
    border-radius: 10px;
  }
  .sub-card > .el-card__body {
    padding: 14px 12px;
  }
  .sub-form > .el-form-item {
    margin-bottom: 20px;
  }
  .advanced-section {
    margin-bottom: 26px !important;
  }
  .result-divider {
    margin: 30px 0 26px;
  }
  .action-group-primary {
    margin-top: 30px;
  }
  .action-group > .el-form-item__content {
    gap: 0;
  }
  /* 提供商+链接行：移动端名称独占一行，链接与删除按钮同行 */
  .sub-link-name {
    margin-bottom: 8px;
  }
  .sub-link-del {
    margin-top: 2px;
  }
  /* 底部操作按钮两行排列、加大触控区域 */
  .action-btn {
    width: 46% !important;
    margin: 4px 2% !important;
  }
  .action-btn-wide {
    width: 96% !important;
    margin: 4px 2% !important;
  }
  /* 结果链接字号缩小防止撑破 */
  .copy-content .el-input__inner {
    font-size: 12px;
  }
  /* 弹窗适配小屏 */
  .el-message-box.msgbox {
    width: 92vw;
  }
}
</style>






