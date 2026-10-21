-- In French, babel puts a thin space before every colon. An identifier with a colon
-- inside it (EPSG:5523, ISO 19160-1:2015) must keep it tight. Runs after citeproc so
-- that it also reaches the reference list; links are left alone.
local french = false

function Meta(m)
  local lang = m.lang and pandoc.utils.stringify(m.lang) or ''
  french = lang:sub(1, 2) == 'fr'
end

local function tight(s)
  if not french or not s.text:find('[%w%-]:[%w]') then
    return nil
  end
  return pandoc.RawInline('latex', '{\\NoAutoSpacing ' .. s.text:gsub('([#%%&_{}$])', '\\%1') .. '}')
end

return {
  { Meta = Meta },
  { traverse = 'topdown', Link = function(l) return l, false end, Code = function(c) return c, false end, Str = tight },
}
