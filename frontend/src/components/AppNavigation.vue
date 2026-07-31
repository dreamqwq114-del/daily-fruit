<template>
  <nav class="bottom-navigation" aria-label="主要页面">
    <RouterLink to="/" aria-label="今日推荐">
      <span aria-hidden="true">今</span>
      <small>今日</small>
    </RouterLink>
    <RouterLink to="/preferences" aria-label="偏好设置">
      <span aria-hidden="true">调</span>
      <small>偏好</small>
    </RouterLink>
    <RouterLink to="/history" aria-label="推荐历史">
      <span aria-hidden="true">记</span>
      <small>历史</small>
    </RouterLink>
  </nav>
</template>
