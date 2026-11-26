<template>
  <span class="demo" :title="$t('Données fictives de démonstration : aucun équipement réel n\'est interrogé')">{{ $t('Démo') }}</span>
</template>

<style scoped>
.demo {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  border-radius: var(--radius-pill);
  background: repeating-linear-gradient(-45deg, #ffb340, #ffb340 6px, #ffc566 6px, #ffc566 12px);
  color: #4a2a00;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  flex: none;
}
</style>
