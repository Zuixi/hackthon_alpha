FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:22-alpine3.21-linuxarm64 AS deps

WORKDIR /app

ARG NPM_REGISTRY=https://registry.npmmirror.com
ENV npm_config_registry=${NPM_REGISTRY} \
    npm_config_fund=false \
    npm_config_audit=false

RUN sed -i 's|https://dl-cdn.alpinelinux.org/alpine|https://mirrors.tuna.tsinghua.edu.cn/alpine|g' /etc/apk/repositories \
    && sed -i 's|http://dl-cdn.alpinelinux.org/alpine|https://mirrors.tuna.tsinghua.edu.cn/alpine|g' /etc/apk/repositories

COPY package*.json ./
RUN npm install --include=optional && npm cache clean --force


FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:22-alpine3.21-linuxarm64 AS runner

WORKDIR /app

ARG NPM_REGISTRY=https://registry.npmmirror.com
ENV NODE_ENV=development \
    npm_config_registry=${NPM_REGISTRY} \
    npm_config_fund=false \
    npm_config_audit=false

RUN sed -i 's|https://dl-cdn.alpinelinux.org/alpine|https://mirrors.tuna.tsinghua.edu.cn/alpine|g' /etc/apk/repositories \
    && sed -i 's|http://dl-cdn.alpinelinux.org/alpine|https://mirrors.tuna.tsinghua.edu.cn/alpine|g' /etc/apk/repositories

COPY --from=deps /app/node_modules ./node_modules
COPY index.html ./
COPY package*.json ./
COPY tsconfig*.json ./
COPY vite.config.ts ./
COPY src ./src

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
