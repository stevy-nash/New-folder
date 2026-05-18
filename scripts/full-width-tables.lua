-- full-width-tables.lua
-- Sets a smaller font size on all text inside table cells for DOCX output.
-- Adjust FONT_SIZE (half-points: 18 = 9pt, 16 = 8pt, 20 = 10pt).

local FONT_SIZE = "18"  -- 8pt

local function esc(s)
    return s:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;")
end

local function pPr_xml()
    return string.format(
        '<w:pPr><w:rPr><w:sz w:val="%s"/><w:szCs w:val="%s"/></w:rPr></w:pPr>',
        FONT_SIZE, FONT_SIZE)
end

local function run_xml(text)
    return string.format(
        '<w:r><w:rPr><w:sz w:val="%s"/><w:szCs w:val="%s"/></w:rPr><w:t xml:space="preserve">%s</w:t></w:r>',
        FONT_SIZE, FONT_SIZE, esc(text))
end

local function prepend_pPr(inlines)
    local result = {pandoc.RawInline("openxml", pPr_xml())}
    for _, v in ipairs(inlines) do result[#result+1] = v end
    return result
end

local cell_filter = {
    Str   = function(s) return pandoc.RawInline("openxml", run_xml(s.text)) end,
    Space = function()  return pandoc.RawInline("openxml", run_xml(" ")) end,
    SoftBreak = function() return pandoc.RawInline("openxml", run_xml(" ")) end,
    Plain = function(p) return pandoc.Plain(prepend_pPr(p.content)) end,
    Para  = function(p) return pandoc.Para(prepend_pPr(p.content)) end,
}

function Table(el)
    -- Set all columns to ColWidthDefault → pandoc emits autofit layout
    if el.colspecs then
        for i = 1, #el.colspecs do
            el.colspecs[i][2] = pandoc.ColWidthDefault
        end
    end
    return pandoc.walk_block(el, cell_filter)
end
