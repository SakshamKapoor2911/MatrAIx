export const meta = {
  name: 'mircoverse-asset-curation',
  description: 'Curate ui/public PNG assets: terrain mapping, character animation frames, decor, discard list — tied to MircoVerse world rules',
  phases: [
    { title: 'Curate', detail: 'parallel: terrain, character, audit' },
    { title: 'Synthesize', detail: 'merge into one asset manifest' },
  ],
}

const ROOT = 'c:/Users/Sky/OneDrive/Desktop/MircoVerse/ui/public'

const WORLD_RULES = [
  'MircoVerse world rules the visuals MUST encode (visuals are tied to rules, not decoration):',
  '- Grid world, integer cells, one agent per cell, moves one cell/tick (8-neighbourhood).',
  '- 5 terrains: desert (default, harsh drain), oasis (water source, replenishes), mountain (impassable ridge), settlement (cluster around centre, mild replenish), ruins (hold death-caches / dropped goods).',
  '- 3 resources per cell/agent: water, food, goods. Water is survival pressure (drains each tick; 0 = death).',
  '- 1 special cell: Atmospheric Siphon at grid centre on a settlement cell; produces water each tick; the contested prize.',
  '- 3 agent stances: friendly, neutral, aggressive.',
  '- 8 agent actions: move, wait, consume, scavenge, trade, talk, attack, signal.',
  '- World conditions: sandstorm (intermittent, raises drain, visual haze), heat zone (lethal drifting region), agent death (permanent; leaves a death-cache in ruins).',
  '- Two scales: 50x50 / 25 agents (detailed science view) and 200x200 / 1000 agents (LOD load view).',
  '- Aesthetic LOCK: restrained research-instrument look; warm charcoal, muted sand/amber, NO neon, NO fantasy branding. Pixel-art tiles fine but must read as a sober instrument.',
].join('\n')

const TERRAIN_SCHEMA = {
  type: 'object',
  required: ['terrainAssets', 'autotile', 'decor', 'siphonAsset', 'notes'],
  properties: {
    terrainAssets: {
      type: 'array',
      description: 'one entry per terrain type',
      items: {
        type: 'object',
        required: ['terrain', 'baseFile', 'tilePx', 'rationale'],
        properties: {
          terrain: { type: 'string', enum: ['desert', 'oasis', 'mountain', 'settlement', 'ruins'] },
          baseFile: { type: 'string', description: 'path under ui/public, e.g. desert/sand.png' },
          autotileFile: { type: 'string', description: 'the _3x3.png blob for this terrain if used, else empty' },
          tilePx: { type: 'integer' },
          rationale: { type: 'string', description: 'why this asset for this terrain, tied to world rules' },
        },
      },
    },
    autotile: {
      type: 'object',
      required: ['blobLayout', 'frameSize', 'howToIndex'],
      properties: {
        blobLayout: { type: 'string', description: 'decoded structure of the 144x48 _3x3 blob: subtile count and arrangement' },
        frameSize: { type: 'integer' },
        howToIndex: { type: 'string', description: 'concrete rule for picking a subtile from a same-terrain neighbour bitmask, OR say a single tile is enough' },
      },
    },
    decor: {
      type: 'array',
      description: 'decor sprites to scatter and on which terrain',
      items: {
        type: 'object',
        required: ['file', 'onTerrain', 'meaning'],
        properties: {
          file: { type: 'string' },
          onTerrain: { type: 'string' },
          meaning: { type: 'string', description: 'what world fact it signals' },
        },
      },
    },
    siphonAsset: { type: 'string', description: 'best asset (or draw procedurally) for the centre Siphon cell, with reason' },
    notes: { type: 'string' },
  },
}

const CHAR_SCHEMA = {
  type: 'object',
  required: ['sheetLayout', 'bodyVariants', 'layers', 'animations', 'stanceMapping', 'actionCues', 'lod', 'notes'],
  properties: {
    sheetLayout: {
      type: 'object',
      required: ['sheetPx', 'framePx', 'cols', 'rows'],
      properties: {
        sheetPx: { type: 'integer' },
        framePx: { type: 'integer' },
        cols: { type: 'integer' },
        rows: { type: 'integer' },
      },
    },
    bodyVariants: { type: 'array', items: { type: 'string' }, description: 'base body sheet files to use as distinct agent appearances' },
    layers: {
      type: 'array',
      description: 'paper-doll layer files composed on top of body, in draw order',
      items: { type: 'object', required: ['file', 'role'], properties: { file: { type: 'string' }, role: { type: 'string' } } },
    },
    animations: {
      type: 'array',
      description: 'which sheet rows/cols correspond to which animation + facing; be concrete',
      items: {
        type: 'object',
        required: ['name', 'row', 'frameCols', 'facing', 'fps'],
        properties: {
          name: { type: 'string', description: 'stand|walk|run|push|pull|jump|death etc' },
          row: { type: 'integer', description: '0-based row in the sheet' },
          frameCols: { type: 'array', items: { type: 'integer' }, description: '0-based column indices in the loop' },
          facing: { type: 'string', enum: ['down', 'up', 'left', 'right', 'n/a'] },
          fps: { type: 'number' },
        },
      },
    },
    stanceMapping: { type: 'string', description: 'how friendly/neutral/aggressive map to appearance without garish color' },
    actionCues: {
      type: 'array',
      description: 'one per contract action: how to show it visually',
      items: {
        type: 'object',
        required: ['action', 'cue'],
        properties: { action: { type: 'string' }, cue: { type: 'string' } },
      },
    },
    lod: { type: 'string', description: 'how to render an agent at 1000-agent scale + the crossover cell size' },
    notes: { type: 'string' },
  },
}

const AUDIT_SCHEMA = {
  type: 'object',
  required: ['discard', 'keep', 'duplicateGroups', 'recommendation'],
  properties: {
    discard: { type: 'array', items: { type: 'object', required: ['file', 'reason'], properties: { file: { type: 'string' }, reason: { type: 'string' } } } },
    keep: { type: 'array', items: { type: 'string' }, description: 'clean canonical source files to keep' },
    duplicateGroups: { type: 'array', items: { type: 'string' }, description: 'sets of redundant files; name the survivor' },
    recommendation: { type: 'string', description: 'which family is the clean source of truth vs the hand-cropped probes' },
  },
}

phase('Curate')

const terrainPrompt =
  'You are curating TERRAIN + DECOR pixel-art assets for the MircoVerse world map renderer.\n' + WORLD_RULES +
  '\n\nAsset location: ' + ROOT +
  '\nUse the Read tool to OPEN and visually inspect (Read renders PNGs):' +
  '\n- Ground sheets (160x240, 16px tiles): desert/sand.png, desert/dry_dirt.png, desert/sandstone.png, desert/slate.png, desert/cobbled_sandstone.png, desert/water.png' +
  '\n- Autotile blobs (144x48): desert/sand_3x3.png, desert/dry_dirt_3x3.png, desert/sandstone_3x3.png, desert/slate_3x3.png. DECODE their internal layout (144x48 of 16px tiles = 9 cols x 3 rows; identify which subtile is which edge/corner so I can autotile).' +
  '\n- Decor: desert/decor_cactus1..5.png, desert/decor_dead_bush1..4.png, desert/tree_palm1..8.png, desert/decor_stone_large1/medium1-2/small1-4.png, desert/decor_remains1..4.png, desert/decor_iris1..8.png' +
  '\n- Glance at *_to_water.png / *_to_land.png / *_extra.png so you know they exist.' +
  '\n\nDecide each of the 5 terrains to a concrete ground asset, the autotile indexing rule, and which decor to scatter on which terrain so decor SIGNALS world facts (remains/bones on ruins = death-cache; palm/iris near oasis = water; cacti on desert; stones on mountain). Sober/instrument-like. Be concrete about pixel offsets. Return the structured object.'

const characterPrompt =
  'You are curating CHARACTER (agent) pixel-art sprites for the MircoVerse renderer.\n' + WORLD_RULES +
  '\n\nAsset location: ' + ROOT + '/character' +
  '\nThis is a Mana Seed paper-doll character base. Use the Read tool to OPEN and inspect:' +
  '\n- Base bodies (512x512): character/char_a_p1/char_a_p1_0bas_humn_v00.png, and char_a_pONE1/char_a_pONE1_0bas_humn_v00.png, char_a_pONE2/char_a_pONE2_0bas_humn_v00.png, char_a_pONE3/char_a_pONE3_0bas_humn_v00.png' +
  '\n- Outfit layers: character/char_a_p1/1out/char_a_p1_1out_fstr_v01.png and char_a_p1/1out/char_a_p1_1out_pfpn_v01.png' +
  '\n- Hair layer: character/char_a_p1/4har/char_a_p1_4har_bob1_v00.png' +
  '\n- Animation guide (READ THIS, it labels rows): character/guides/animations, page 1.png' +
  '\n- Paper-doll guide: character/guides/paper doll demonstration.png' +
  '\n\nGROUND TRUTH already measured (verify visually): every sheet is 512x512 = 8 cols x 8 rows of 64x64 frames. Guide shows top block stand(4 dirs)/push/pull/jump; bottom block walk(6 frames/dir) + run. Determine CONCRETELY which row index holds which animation and facing, and which column indices form each loop. Confirm facing order (down/up/left/right) from the sprites.' +
  '\n\nThen decide: which body sheets = distinct agent appearances; paper-doll layer draw order; how 3 stances map to appearance WITHOUT garish recoloring; a visual cue for EACH of the 8 actions (move,wait,consume,scavenge,trade,talk,attack,signal) using animation/overlay/bubble (ts_bubble_whisper/ts_bubble_broadcast exist in the parent folder); and LOD for 1000 agents (what to draw instead of a 64px sprite + crossover cell size). Return the structured object.'

const auditPrompt =
  'You are auditing the MircoVerse ui/public asset folder to separate CLEAN canonical sources from BADLY-CROPPED probe images (user said "some are not crop well").\n' + WORLD_RULES +
  '\n\nAsset location: ' + ROOT +
  '\nTwo families exist: (A) CLEAN sources desert/*.png (uniform 16px sheets) + character/**/*.png (uniform 512x512 sheets). (B) HAND-CROPPED probes, odd sizes: ts_*.png, tile_*.png, t2_*.png, t3_*.png, tileset.png/tileset2.png/tileset3.png, inspect_*.png, confirm_*.png.' +
  '\nUse the Read tool to OPEN a representative sample of family (B): ts_sand_a.png, ts_agent_neutral.png, ts_siphon.png, ts_bubble_whisper.png, tileset.png, t3_sand_a.png, inspect_agents.png, confirm_t3_agents.png. Judge crop quality.' +
  '\nDecide which probe files are genuinely reusable (e.g. a clean siphon or bubble icon) vs throwaway debug crops/screenshots to delete. The clean desert/* + character/* families are almost certainly the source of truth. Do NOT delete anything; just classify. Return the structured object.'

const [t, c, a] = await Promise.all([
  agent(terrainPrompt, { label: 'curate:terrain', phase: 'Curate', schema: TERRAIN_SCHEMA }),
  agent(characterPrompt, { label: 'curate:character', phase: 'Curate', schema: CHAR_SCHEMA }),
  agent(auditPrompt, { label: 'curate:audit', phase: 'Curate', schema: AUDIT_SCHEMA }),
])

phase('Synthesize')
const synthPrompt =
  'Merge these three asset-curation results into ONE coherent asset manifest for a canvas renderer of the MircoVerse world. Resolve conflicts; ensure terrain mapping + character layout + discard list are mutually consistent; produce a single plan a developer can implement directly.\n\n' +
  'TERRAIN RESULT:\n' + JSON.stringify(t, null, 2) +
  '\n\nCHARACTER RESULT:\n' + JSON.stringify(c, null, 2) +
  '\n\nAUDIT RESULT:\n' + JSON.stringify(a, null, 2) +
  '\n\nReturn a thorough markdown manifest with sections: Terrain tiles (file to terrain + autotile rule), Decor placement rules, Character sheet geometry (exact frame map: row to animation to facing to columns to fps), Body/layer composition, Stance mapping, Action to visual-cue table (all 8), World-condition visuals (storm/heat/siphon/death), LOD strategy (25 vs 1000), Files-to-delete list. Be concrete with pixel offsets and file paths.'

const manifest = await agent(synthPrompt, { label: 'synthesize:manifest', phase: 'Synthesize' })

return { manifest, terrain: t, character: c, audit: a }
