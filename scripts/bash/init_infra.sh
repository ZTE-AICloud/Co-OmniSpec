#!/bin/bash

PLUGIN_ROOT=$1
PROJECT_ROOT=$PWD

git_init(){
	if [ ! -d '.git' ]; then
		git init . >/dev/null
	fi
}

# 如果是首次执行，需要将 infra 拷贝 到项目目录下 .infra 中
prepare_infra(){
	plugin_infra="${PLUGIN_ROOT}/infra"
	project_infra="${PROJECT_ROOT}/.infra"
	if [ ! -d "$plugin_infra" ]; then
		echo "[错误]插件数据不全：$plugin_infra"
		exit 2
	fi

	if [ ! -d "$project_infra" ]; then
		cp -r "${plugin_infra}" "${project_infra}"
		git add ".infra" >/dev/null
		git commit -m "[SDD] add .infra for SDD" >/dev/null
		exit 1
	fi
}

main(){
	git_init
	prepare_infra "$@"
}

main "$@"

exit 0