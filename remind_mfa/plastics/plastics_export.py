import flodym as fd
import numpy as np
import pandas as pd

from plotly import colors as plc
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pyam
from typing import TYPE_CHECKING
import flodym.export as fde
from typing import Any, List, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.colors as pc


from remind_mfa.common.common_export import CommonDataExporter

if TYPE_CHECKING:
    from remind_mfa.plastics.plastics_model import PlasticsModel


class PlasticsDataExporter(CommonDataExporter):

    # Dictionary of variable names vs names displayed in figures. Used by visualization routines.
    _display_names: dict = {
        "sysenv": "System environment",
        "virginfoss": "Prim(fossil)",
        "virginbio": "Prim(biomass)",
        "virgindaccu": "Prim(daccu)",
        "virginccu": "Prim(ccu)",
        "virgin": "Prim(total)",
        "processing": "Proc",
        "fabrication": "Fabri",
        "reclmech": "Mech recycling",
        "reclchem": "Chem recycling",
        "use": "Use Phase",
        "eol": "EoL",
        "collected": "Collect",
        "mismanaged": "Uncollected",
        "incineration": "Incineration",
        "landfill": "Landfill",
        "uncontrolled": "Uncontrolled",
        "emission": "Emissions",
        "captured": "Captured",
        "atmosphere": "Atmosphere",
        "waste_market": "Waste Market",
        "primary_market": "Prim Market",
        "intermediate_market": "Inter Market",
        "good_market": "Good Market",
    }

    # _display_names: dict = {
    #     "sysenv": "系统环境",
    #     "virginfoss": "初级(化石)",
    #     "virginbio": "初级(生物质)",
    #     "virgindaccu": "初级(直接空气捕获)",
    #     "virginccu": "初级(碳捕获利用)",
    #     "virgin": "初级(总计)",
    #     "processing": "加工",
    #     "fabrication": "制造",
    #     "reclmech": "机械回收",
    #     "reclchem": "化学回收",
    #     "use": "使用阶段",
    #     "eol": "生命周期终端",
    #     "collected": "收集",
    #     "mismanaged": "未收集",
    #     "incineration": "焚烧",
    #     "landfill": "填埋",
    #     "uncontrolled": "无控制处置",
    #     "emission": "排放",
    #     "captured": "捕获",
    #     "atmosphere": "大气",
    #     "waste_imports": "废料进口",
    #     "waste_exports": "废料出口",
    #     "waste_market": "废料市场",
    #     "primary_imports": "初级进口",
    #     "primary_exports": "初级出口",
    #     "primary_market": "初级市场",
    #     "intermediate_imports": "中间产品进口",
    #     "intermediate_exports": "中间产品出口",
    #     "intermediate_market": "中间产品市场",
    #     "final_imports": "最终产品进口",
    #     "final_exports": "最终产品出口",
    #     "good_market": "产品市场",
    # }

    def visualize_results(self, model: "PlasticsModel"):
        if not self.cfg.do_visualize:
            return

        self.export_eol_data_by_region_and_year(mfa=model.mfa_future)
        self.export_use_data_by_region_and_year(mfa=model.mfa_future)
        self.export_production_data_by_region_and_year(mfa=model.mfa_future)
        self.export_recycling_data_by_region_and_year(mfa=model.mfa_future)
        self.export_stock_extrapolation(model=model)
        self.export_stock(model=model)
        self.export_stock_by_region(model=model)

        if self.do_export.iamc:
            self.write_iamc(mfa=model.mfa_future)

        if self.cfg.production["do_visualize"]:
            self.visualize_demand(mfa=model.mfa_future)

        if self.cfg.extrapolation["do_visualize"]:
            self.visualize_extrapolation(model=model)

        if self.cfg.use_stock["do_visualize"]:
            self.visualize_stock(mfa=model.mfa_future, subplots_by_good=False)

        if self.cfg.sankey["do_visualize"]:
            self.visualize_sankey(mfa=model.mfa_future)

        if self.cfg.flows["do_visualize"]:
            primary_production = (
                model.mfa_future.flows["virginfoss => virgin"]
                + model.mfa_future.flows["virginbio => virgin"]
                + model.mfa_future.flows["virgindaccu => virgin"]
                + model.mfa_future.flows["virginccu => virgin"]
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=primary_production,
                name="Primary production",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["virgin => processing"],
                name="Domestic primary production",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["reclmech => processing"],
                name="Mechanical recycling",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["reclchem => virgin"],
                name="Chemical recycling",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["eol => collected"],
                name="Collected",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["collected => landfill"],
                name="Landfilled",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.stocks["in_use"].inflow,
                name="Demand",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["fabrication => good_market"],
                name="Final exports",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["good_market => use"],
                name="Final imports",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["processing => intermediate_market"],
                name="Intermediate exports",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["intermediate_market => fabrication"],
                name="Intermediate imports",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["virgin => primary_market"],
                name="Primary exports",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["primary_market => processing"],
                name="Primary imports",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["collected => waste_market"],
                name="Waste exports",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["waste_market => collected"],
                name="Waste imports",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            self.visualize_flow(
                mfa=model.mfa_future,
                flow=model.mfa_future.flows["fabrication => use"],
                name="Domestic Fabrication",
                subplot_dim="Region",
                linecolor_dim="Material",
            )
            
            # EoL fate rates (recycling / incineration / landfill)
            self.visualize_eol_rates(mfa=model.mfa_future)
            
        #self.stop_and_show()
        print("Visualization completed. Charts are saved and displayed.")
        
    def visualize_flow(
        self, mfa: fd.MFASystem, flow: fd.Flow, name: str, subplot_dim=None, linecolor_dim=None, y_label: str = "Flow [Mt]",
    ):

        x_array = None
        x_label = "Year"
        y_label = y_label
        subplot_dimletter = ()
        linecolor_dimletter = ()
        if subplot_dim is not None:
            subplot_dimletter = next(
                dimlist.letter for dimlist in mfa.dims.dim_list if dimlist.name == subplot_dim
            )
        if linecolor_dim is not None:
            linecolor_dimletter = next(
                dimlist.letter for dimlist in mfa.dims.dim_list if dimlist.name == linecolor_dim
            )
        sum_dims = tuple(
            x for x in flow.dims.letters if x not in (subplot_dimletter, linecolor_dimletter, "t")
        )
        flow = flow.sum_over(sum_dims)

        if subplot_dim == "Region":
            title = f"Regional {name} Flow"
            tag = "_regional"
        elif subplot_dim == "Material":
            title = f"Material {name} Flow"
            tag = "_perMaterial"
        elif subplot_dim == "Good":
            title = f"Good {name} Flow"
            tag = "_perGood"
        else:
            subplot_dim = None
            tag = ""
            title = f"Global {name} Flow"

        ap = self.plotter_class(
            array=flow,
            intra_line_dim="Time",
            linecolor_dim=linecolor_dim,
            subplot_dim=subplot_dim,
            x_array=x_array,
            title=title,
            line_type="dot",
            x_label=x_label,
            y_label=y_label,
        )
        self.plot_and_save_figure(ap, f"{name}_flow{tag}.png")

    def visualize_demand(self, mfa: fd.MFASystem):
        import numpy as np
        import colorsys
        import matplotlib.cm as cm
        import matplotlib.colors as mcolors

        # ========= 读取地区设置 =========
        def _cfg_get(path, default=None):
            obj = self.cfg
            for k in path:
                try:
                    obj = obj[k] if isinstance(obj, dict) else getattr(obj, k)
                except (KeyError, AttributeError, TypeError):
                    return default
            return obj

        region_sel = (_cfg_get(["sankey", "slice_dict", "r"]) or 
                    _cfg_get(["production", "region"]) or 
                    _cfg_get(["demand", "region"]) or 
                    _cfg_get(["region"]))

        print(f"DEBUG: Region setting: {region_sel}")

        # ========= Colormap 配色方案 =========
        def _get_cmap_colors(cmap_name, n_colors):
            """从 matplotlib colormap 获取颜色"""
            cmap = cm.get_cmap(cmap_name)
            colors = []
            for i in range(n_colors):
                rgba = cmap(i / (n_colors - 1))
                hex_color = mcolors.rgb2hex(rgba[:3])
                colors.append(hex_color)
            return colors

        def _adjust_colormap_colors(colors, sat_mult=1.0, light_add=0.0):
            """调整 colormap 颜色的饱和度和亮度"""
            adjusted = []
            for hex_color in colors:
                # 转换为 RGB
                rgb = mcolors.hex2color(hex_color)
                # 转换为 HLS
                h, l, s = colorsys.rgb_to_hls(*rgb)
                # 调整亮度和饱和度
                l = min(1.0, l + light_add)
                s = max(0.0, min(1.0, s * sat_mult))
                # 转换回 RGB 和 hex
                rgb_new = colorsys.hls_to_rgb(h, l, s)
                hex_new = mcolors.rgb2hex(rgb_new)
                adjusted.append(hex_new)
            return adjusted

        # ========= 数据选择 =========
        def _select_region_or_global(arr):
            if region_sel:
                try:
                    return arr[{"r": region_sel}]
                except Exception as e:
                    print(f"Warning: Could not select region '{region_sel}': {e}")
            return arr.sum_over(("r",))

        def _sum_over_safe(arr, dims):
            for d in dims:
                try:
                    arr = arr.sum_over((d,))
                except Exception:
                    pass
            return arr

        # ========= Colormap 配色方案设置 =========
        # 使用不同的 colormap 生成配色
        n_colors = 12  # 根据您的数据类别数量调整
        
        # 主线条颜色 - 使用 viridis 或 tab10
        base_colors = _get_cmap_colors('tab10', n_colors)
        
        # 历史线条颜色 - 使用相同颜色但调整饱和度和亮度
        hist_colors = _adjust_colormap_colors(base_colors, sat_mult=0.6, light_add=0.3)
        
        # 堆叠面积颜色 - 使用 Set3 或其他柔和的 colormap
        stacked_colors = _get_cmap_colors('Set3', n_colors)
        
        # 扩展颜色列表以避免索引越界
        base_colors = (base_colors * 10)[:256]
        hist_colors = (hist_colors * 10)[:256]
        stacked_colors = (stacked_colors * 10)[:256]

        # ========= 样式设置 =========
        def _style(fig):
            if getattr(self.cfg, "plotting_engine", "plotly") == "plotly":
                fig.update_layout(
                    template="simple_white",
                    font=dict(family="Arial, DejaVu Sans, Helvetica", size=14),
                    title=dict(font=dict(size=18), y=0.98),
                    margin=dict(l=70, r=30, t=80, b=110),
                    legend=dict(
                        orientation="h", 
                        xanchor="left", 
                        x=0.0, 
                        yanchor="top", 
                        y=-0.12,
                        font=dict(size=28)
                    ),
                    showlegend=True,
                )
                fig.update_xaxes(
                    showline=True, 
                    linewidth=1, 
                    linecolor="#333333", 
                    gridcolor="rgba(0,0,0,0.08)", 
                    ticklen=4,
                    tickfont=dict(size=24),
                    title_font=dict(size=28)  # 修正：使用 title_font 而不是 titlefont
                )
                fig.update_yaxes(
                    showline=True, 
                    linewidth=1, 
                    linecolor="#333333", 
                    gridcolor="rgba(0,0,0,0.08)", 
                    ticklen=4,
                    tickfont=dict(size=24),
                    title_font=dict(size=28)  # 修正：使用 title_font 而不是 titlefont
                )

        # ========= 1) 需求对比图：Modelled vs Historic =========
        region_suffix = f" — {region_sel}" if region_sel else " — Global"
        
        # 模型数据
        modeled_array = _select_region_or_global(mfa.stocks["in_use"].inflow)
        modeled_array = _sum_over_safe(modeled_array, ("m", "e"))
        
        ap_modeled = self.plotter_class(
            array=modeled_array,
            intra_line_dim="Time",
            subplot_dim="Good",
            line_label="Modelled",
            display_names=self._display_names,
            color_map=base_colors,
            title=f"Plastic Demand{region_suffix}",
        )
        fig = ap_modeled.plot()

        # 历史数据
        hist_array = _select_region_or_global(mfa.parameters["consumption"])
        hist_array = _sum_over_safe(hist_array, ("r",))
        
        ap_historic = self.plotter_class(
            array=hist_array,
            intra_line_dim="Historic Time",
            subplot_dim="Good",
            line_label="Historic",
            fig=fig,
            xlabel="Year",
            ylabel="Demand [Mt]",
            display_names=self._display_names,
            color_map=hist_colors,
            line_type="dot",
        )
        fig = ap_historic.plot()
        _style(fig)

        # 添加图例
        if getattr(self.cfg, "plotting_engine", "plotly") == "plotly":
            import plotly.graph_objects as go
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                                name="Modelled", line=dict(color=base_colors[0], width=2)))
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                                name="Historic", line=dict(color=hist_colors[0], width=2, dash="dot")))

        filename_suffix = f"_{region_sel}" if region_sel else "_global"
        self.plot_and_save_figure(ap_historic, f"demand{filename_suffix}.png")

        # ========= 2) 堆叠面积图：Inflow / Outflow / Stock =========
        # 获取数据
        inflow = _sum_over_safe(_select_region_or_global(mfa.stocks["in_use"].inflow), ("m", "e"))
        outflow = _sum_over_safe(_select_region_or_global(mfa.stocks["in_use"].outflow), ("m", "e"))
        stock = _sum_over_safe(_select_region_or_global(mfa.stocks["in_use"].stock), ("m", "e"))

        # 累积求和用于堆叠
        good_dim = inflow.dims.index("g")
        inflow_cumsum = inflow.apply(np.cumsum, kwargs={"axis": good_dim})
        outflow_cumsum = outflow.apply(np.cumsum, kwargs={"axis": good_dim})
        stock_cumsum = stock.apply(np.cumsum, kwargs={"axis": good_dim})

        # 总量线
        inflow_total = _sum_over_safe(inflow, ("g",))

        # 绘制三个图表
        for name, data_cumsum in [("inflow", inflow_cumsum), ("outflow", outflow_cumsum), ("stock", stock_cumsum)]:
            ap_area = self.plotter_class(
                array=data_cumsum,
                intra_line_dim="Time",
                linecolor_dim="Good",
                chart_type="area",
                display_names=self._display_names,
                title=f"{name.title()} [Mt]{region_suffix}",
                color_map=stacked_colors,
            )
            fig_area = ap_area.plot()
            
            # 添加总量线
            ap_line = self.plotter_class(
                array=inflow_total,
                intra_line_dim="Time",
                fig=fig_area,
                line_label="Inflow (total)",
                color_map=["#000000"] * 100,
            )
            fig_area = ap_line.plot()
            _style(fig_area)
            self.plot_and_save_figure(ap_line, f"{name}_stacked{filename_suffix}.png", do_plot=False)



    def visualize_stock(self, mfa: fd.MFASystem, subplots_by_good=False):

        stock = mfa.stocks["in_use"].stock.sum_over(("r", "m", "e"))
        good_dim = stock.dims.index("g")
        stock = stock.apply(np.cumsum, kwargs={"axis": good_dim})
        ap = self.plotter_class(
            array=stock,
            intra_line_dim="Time",
            linecolor_dim="Good",
            chart_type="area",
            display_names=self._display_names,
            title="Stock [Mt]",
        )
        fig = ap.plot()
        self.plot_and_save_figure(ap, "stock_stacked.png", do_plot=False)

        per_capita = self.cfg.use_stock["per_capita"]

        stock = mfa.stocks["in_use"].stock * 1000 * 1000
        population = mfa.parameters["population"]
        x_array = None

        pc_str = " pC" if per_capita else ""
        x_label = "Year"
        y_label = f"Plastic Stock{pc_str} [t]"
        title = f"Plastic Stocks{pc_str}"
        if self.cfg.use_stock.get("over_gdp", False):
            title = title + f" over GDP{pc_str}"
            x_label = f"GDP/PPP{pc_str} [2005 USD]"
            x_array = mfa.parameters["gdppc"]
            if not per_capita:
                x_array = x_array * population

        if subplots_by_good:
            subplot_dim = {"subplot_dim": "Good"}
        else:
            subplot_dim = {}
            stock = stock.sum_over("g")
        stock = stock.sum_over(["e", "m"])

        if per_capita:
            stock = stock / population

        colors = plc.qualitative.Dark24
        colors = (
            colors[: stock.dims["r"].len]
            + colors[: stock.dims["r"].len]
            + ["black" for _ in range(stock.dims["r"].len)]
        )

        ap_stock = self.plotter_class(
            array=stock,
            intra_line_dim="Time",
            linecolor_dim="Region",
            **subplot_dim,
            display_names=self._display_names,
            x_array=x_array,
            xlabel=x_label,
            ylabel=y_label,
            title=title,
            color_map=colors,
            line_type="dot",
            suppress_legend=True,
        )
        fig = ap_stock.plot()

        hist_stock = stock[{"t": mfa.dims["h"]}]
        hist_x_array = x_array[{"t": mfa.dims["h"]}] if x_array is not None else None
        ap_hist_stock = self.plotter_class(
            array=hist_stock,
            intra_line_dim="Historic Time",
            linecolor_dim="Region",
            **subplot_dim,
            display_names=self._display_names,
            x_array=hist_x_array,
            fig=fig,
            color_map=colors,
        )
        fig = ap_hist_stock.plot()

        last_year_dim = fd.Dimension(
            name="Last Historic Year", letter="l", items=[mfa.dims["h"].items[-1]]
        )
        scatter_stock = hist_stock[{"h": last_year_dim}]
        scatter_x_array = hist_x_array[{"h": last_year_dim}] if hist_x_array is not None else None
        ap_scatter_stock = self.plotter_class(
            array=scatter_stock,
            intra_line_dim="Last Historic Year",
            linecolor_dim="Region",
            **subplot_dim,
            display_names=self._display_names,
            x_array=scatter_x_array,
            fig=fig,
            chart_type="scatter",
            color_map=colors,
            suppress_legend=True,
        )
        fig = ap_scatter_stock.plot()

        # if self.cfg.plotting_engine == "plotly":
        #     fig.update_xaxes(type="log", range=[3, 5])
        # elif self.cfg.plotting_engine == "pyplot":
        #     for ax in fig.get_axes():
        #         ax.set_xscale("log")
        #         ax.set_xlim(1e3, 1e5)

        self.plot_and_save_figure(
            ap_scatter_stock,
            f"plastic_stocks_global_by_region{'_per_capita' if per_capita else ''}.png",
            do_plot=False,
        )

    def visualize_eol_rates(self, mfa: fd.MFASystem):
        """
        Visualize recycling, incineration and landfill rates
        (share of collected plastic going to each fate) by region over time.
        """

        # 1. Define the main EoL fate flows
        #    If you also have 'collected => uncontrolled', you can add it
        #    to 'total' as well – here we only use recycling/incineration/landfill.
        recl = (
            mfa.flows["collected => reclmech"]
            + mfa.flows["collected => reclchem"]
        )
        incin = mfa.flows["collected => incineration"]
        landfill = mfa.flows["collected => landfill"]

        # 2. Aggregate across all non-(Region, Time) dimensions
        def _sum_to_rt(arr: fd.FlodymArray) -> fd.FlodymArray:
            # Keep only region ('r') and time ('t') dimensions
            keep_letters = ("r", "t")
            sum_letters = tuple(
                letter for letter in arr.dims.letters if letter not in keep_letters
            )
            if len(sum_letters) == 0:
                return arr
            return arr.sum_over(sum_letters)

        recl_rt = _sum_to_rt(recl)
        incin_rt = _sum_to_rt(incin)
        landfill_rt = _sum_to_rt(landfill)

        total_rt = recl_rt + incin_rt + landfill_rt

        # 3. Convert to rates [% of total collected going to each fate]
        #    Add a tiny epsilon to avoid division by zero.
        eps = 1e-12
        total_safe = total_rt + eps

        recl_rate = recl_rt / total_safe * 100.0
        incin_rate = incin_rt / total_safe * 100.0
        landfill_rate = landfill_rt / total_safe * 100.0

        # 4. Plot each rate by region
        #    We reuse visualize_flow so that style is consistent.
        self.visualize_flow(
            mfa=mfa,
            flow=recl_rate,
            name="Recycling rate",
            subplot_dim="Region",
            linecolor_dim=None,
            y_label="Share of collected plastic [%]",
        )

        self.visualize_flow(
            mfa=mfa,
            flow=incin_rate,
            name="Incineration rate",
            subplot_dim="Region",
            linecolor_dim=None,
            y_label="Share of collected plastic [%]",
        )

        self.visualize_flow(
            mfa=mfa,
            flow=landfill_rate,
            name="Landfill rate",
            subplot_dim="Region",
            linecolor_dim=None,
            y_label="Share of collected plastic [%]",
        )


    def visualize_sankey(self, mfa: fd.MFASystem):
        """
        绘制桑基图（支持中文显示，避免 dict(tr.node) 转换错误）。
        依赖：fde.PlotlySankeyPlotter、self._display_names、self._show_and_save_plotly。
        """
        import platform
        import plotly.graph_objects as go

        # ============== 中文字体：跨平台 fallback ==============
        def chinese_font_family() -> str:
            sys = platform.system()
            if sys == "Windows":
                return "Microsoft YaHei, SimHei, DengXian, Arial Unicode MS, Noto Sans CJK SC, sans-serif"
            elif sys == "Darwin":  # macOS
                return "PingFang SC, Hiragino Sans GB, Heiti SC, STHeiti, Arial Unicode MS, Noto Sans CJK SC, sans-serif"
            else:  # Linux / Server
                # 确保系统安装了 Noto 或 思源黑体：fonts-noto-cjk / source-han-sans-cn
                return "Noto Sans CJK SC, Source Han Sans SC, WenQuanYi Micro Hei, Arial Unicode MS, DejaVu Sans, sans-serif"

        CN_FONT = chinese_font_family()

        # ============== 配色 ==============
        production_color = "#EDC948"
        use_color        = "#9EC3D5"
        eol_color        = "#499894"
        recycle_color    = "#86BCB6"
        emission_color   = "#E15759"
        trade_color      = "#D37295"

        # ============== 流颜色映射（默认生产色） ==============
        flow_color_dict = {"default": production_color}

        # use 流
        flow_color_dict.update({
            fn: use_color
            for fn, f in mfa.flows.items()
            if getattr(f.from_process, "name", "") == "use" or getattr(f.to_process, "name", "") == "use"
        })
        # EoL 流
        flow_color_dict.update({
            fn: eol_color
            for fn, f in mfa.flows.items()
            if getattr(f.from_process, "name", "") in ("eol", "collected")
        })
        # 排放/损失流
        flow_color_dict.update({
            fn: emission_color
            for fn, f in mfa.flows.items()
            if getattr(f.to_process, "name", "") in ("atmosphere", "mismanaged", "incineration", "uncontrolled", "emission")
        })
        # 回收流
        flow_color_dict.update({
            fn: recycle_color
            for fn, f in mfa.flows.items()
            if getattr(f.from_process, "name", "") in ("reclmech", "reclchem")
            or getattr(f.to_process, "name", "") in ("reclmech", "reclchem")
        })
        # 贸易流（可选：按名称包含 trade/import/export 归类）
        trade_keywords = {"trade", "import", "export"} # 使用更简洁的关键字
        flow_color_dict.update({
            fn: trade_color
            for fn, f in mfa.flows.items()
            if any(keyword in getattr(f.from_process, "name", "").lower() for keyword in trade_keywords)
            or any(keyword in getattr(f.to_process, "name", "").lower() for keyword in trade_keywords)
        })

        # ============== Sankey 布局参数（合并到 cfg） ==============
        try:
            sankey_cfg = dict(self.cfg.sankey)
        except Exception:
            sankey_cfg = {}
        sankey_cfg.update({
            "valueformat": ".2s",        # 科学计数，两位有效数字
            "node_pad": 15,              # 节点间距
            "node_thickness": 20,        # 节点厚度
            "arrangement": "snap",       # 减少边交叉
            "flow_color_dict": flow_color_dict,
            "node_color_dict": {"default": "gray", "use": "black"},
            # 如果 Plotter 支持透传 textfont / node_textfont，这里一并给出（不支持也无碍）
            "textfont": {"family": CN_FONT, "size": 18, "color": "black"},
            "node_textfont": {"family": CN_FONT, "size": 18, "color": "black"},
        })
        self.cfg.sankey = sankey_cfg

        # ============== 构建并绘图 ==============
        display_names_fmt = {k: f"<b>{v}</b>" for k, v in self._display_names.items()}
        plotter = fde.PlotlySankeyPlotter(
            mfa=mfa,
            display_names=display_names_fmt,
            **self.cfg.sankey
        )
        fig = plotter.plot()

        # ============== 图例（方块占位） ==============
        legend_entries = [
            (production_color, "Production"),
            (eol_color, "End-of-Life"),
            (recycle_color, "Recycling"),
            (use_color, "Use"),
            (emission_color, "Losses"),
            (trade_color, "Trade"),
        ]
        for color, label in legend_entries:
            fig.add_trace(
                go.Scatter(
                    mode="markers",
                    x=[None], y=[None],
                    marker=dict(size=10, color=color, symbol="square"),
                    name=label,
                    showlegend=True,
                )
            )

        # ============== 布局与中文字体生效（关键） ==============
        fig.update_layout(
            font=dict(family=CN_FONT, size=18, color="black"),
            showlegend=True,
            plot_bgcolor="rgba(0,0,0,0)",
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)

        # 将中文字体应用到 sankey 文本与悬浮框（避免直接操作 tr.node）
        fig.update_traces(
            selector=dict(type="sankey"),
            textfont=dict(family=CN_FONT),
            hoverlabel=dict(font=dict(family=CN_FONT)),
        )

        # ===== 字体大小（自己改数值） =====
        SIZE_NODE  = 24  # 节点文字（Sankey label）
        SIZE_GLOBAL= 20   # 全局/图例/hover

        # 节点标签 & 悬浮框
        fig.update_traces(
            selector=dict(type="sankey"),
            textfont=dict(family=CN_FONT, size=SIZE_NODE),                  # 节点文字变大
            hoverlabel=dict(font=dict(family=CN_FONT, size=SIZE_GLOBAL)),   # 悬浮框文字变大
        )

        # ============== 显示/保存 ==============
        self._show_and_save_plotly(fig, name="sankey")



    def visualize_extrapolation(self, model: "PlasticsModel"):
        import numpy as np
        import colorsys

        try:
            import matplotlib as mpl
        except Exception:
            mpl = None

        # ---------- 数据 ----------
        mfa = model.mfa_future
        per_capita = self.cfg.use_stock["per_capita"]
        subplot_dim = "Region"
        linecolor_dim = "Good"
        stock = mfa.stocks["in_use"].stock
        population = mfa.parameters["population"]
        x_array = None

        pc_str = "pC" if per_capita else ""
        x_label = "Year"
        y_label = f"Stock{pc_str} [t]"
        title = f"Stock Extrapolation: Historic and Projected vs Pure Prediction"

        dimlist = ["t"]
        if subplot_dim is not None:
            subplot_dimletter = next(d.letter for d in mfa.dims.dim_list if d.name == subplot_dim)
            dimlist.append(subplot_dimletter)
        if linecolor_dim is not None:
            linecolor_dimletter = next(d.letter for d in mfa.dims.dim_list if d.name == linecolor_dim)
            dimlist.append(linecolor_dimletter)

        other_dimletters = tuple(letter for letter in stock.dims.letters if letter not in dimlist)
        stock = stock.sum_over(other_dimletters) * 1000 * 1000
        other_dimletters = tuple(
            letter
            for letter in model.mfa_future.stock_handler.pure_prediction.dims.letters
            if letter not in dimlist
        )
        pure_prediction = (
            model.mfa_future.stock_handler.pure_prediction.sum_over(other_dimletters) * 1000 * 1000
        )

        # ---------- X轴可选：GDP ----------
        if self.cfg.use_stock["over_gdp"]:
            title = title + f" over GDP{pc_str}"
            x_label = f"GDP/PPP{pc_str} [2005 USD]"
            x_array = mfa.parameters["gdppc"].cast_to(stock.dims)
            if self.cfg.use_stock["acc"]:
                x_array[...] = np.maximum.accumulate(x_array.values, axis=0)
                x_label = f"GDPacc/PPP{pc_str} [2005 USD]"
            if not per_capita:
                x_array = x_array * population

        if per_capita:
            stock = stock / population

        # ---------- 风格（更新：图例放底部 + 调整边距） ----------
        def _apply_matplotlib_nature_style(fig):
            if mpl is None:
                return
            rc = {
                "font.family": "DejaVu Sans",
                "font.size": 10.5,
                "axes.titlesize": 12.5,
                "axes.labelsize": 11,
                "axes.edgecolor": "#333333",
                "axes.linewidth": 0.9,
                "axes.facecolor": "white",
                "axes.grid": False,
                "xtick.major.size": 3.5,
                "xtick.major.width": 0.9,
                "ytick.major.size": 3.5,
                "ytick.major.width": 0.9,
                "lines.linewidth": 1.9,
                "savefig.dpi": 300,
                "figure.dpi": 120,
            }
            with mpl.rc_context(rc):
                for ax in fig.get_axes():
                    for side in ["top", "right"]:
                        ax.spines[side].set_visible(False)
                # 关键：给标题和底部图例留白
                try:
                    fig.subplots_adjust(top=0.92, bottom=0.20)
                except Exception:
                    pass

        def _apply_plotly_nature_style(fig):
            # 关键：图例移到底部，增加底部边距，避免与标题重叠
            fig.update_layout(
                template="simple_white",
                font=dict(family="Arial, DejaVu Sans, Helvetica", size=11),
                title=dict(font=dict(size=14), y=0.985),
                margin=dict(l=60, r=24, t=72, b=110),
                legend=dict(
                    orientation="h",
                    xanchor="left", x=0.0,
                    yanchor="top",  y=-0.14  # 放到图外下方
                ),
                showlegend=True,
                legend_tracegroupgap=8,
            )
            fig.update_xaxes(showline=True, linewidth=1, linecolor="#333333",
                            mirror=False, zeroline=False, gridcolor="rgba(0,0,0,0.08)", ticklen=4)
            fig.update_yaxes(showline=True, linewidth=1, linecolor="#333333",
                            mirror=False, zeroline=False, gridcolor="rgba(0,0,0,0.08)", ticklen=4)

        # ---------- 颜色工具（全部输出 hex 字符串） ----------
        def _to_rgba01(c):
            if isinstance(c, str):
                s = c.strip().lower()
                if s.startswith("#"):
                    s = s.lstrip("#")
                    if len(s) == 3:
                        r, g, b = (int(s[i] * 2, 16) for i in range(3))
                    elif len(s) == 6:
                        r, g, b = (int(s[i:i+2], 16) for i in (0, 2, 4))
                    else:
                        return (0.22, 0.22, 0.22, 1.0)
                    return (r/255, g/255, b/255, 1.0)
                if mpl is not None:
                    try:
                        return mpl.colors.to_rgba(c)
                    except Exception:
                        return (0.22, 0.22, 0.22, 1.0)
                return (0.22, 0.22, 0.22, 1.0)
            if isinstance(c, (tuple, list)) and len(c) in (3, 4):
                vals = list(c) + ([1.0] if len(c) == 3 else [])
                r, g, b, a = vals[:4]
                if max(r, g, b, a) > 1.0:
                    r, g, b, a = r/255, g/255, b/255, a/255
                return (float(r), float(g), float(b), float(a))
            return (0.22, 0.22, 0.22, 1.0)

        def _rgba01_to_hex(rgba):
            r, g, b, _ = rgba
            return "#{:02x}{:02x}{:02x}".format(
                int(round(r*255)), int(round(g*255)), int(round(b*255))
            )

        def _adjacent_variant_str(c_str, light_add=0.35, sat_mult=0.60, hue_shift_deg=12.0):
            """同色系但更易分辨：更亮、更低饱和，并小幅度色相偏移。"""
            r, g, b, a = _to_rgba01(c_str)
            h, l, s = colorsys.rgb_to_hls(r, g, b)
            l = min(1.0, l + light_add)
            s = max(0.0, s * sat_mult)
            h = (h + hue_shift_deg / 360.0) % 1.0
            r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
            return _rgba01_to_hex((r2, g2, b2, a))

        def _nature_base_palette(n):
            base = [
                "#374E55", "#DF8F44", "#00A1D5", "#B24745", "#79AF97",
                "#6A6599", "#80796B", "#4E84C4", "#C4961A"
            ]
            if n <= len(base):
                return base[:n]
            k = (n + len(base) - 1) // len(base)
            return (base * k)[:n]

        def _extend_palette(pal, nmin=512):
            pal = pal or ["#4E84C4"]
            times = (nmin + len(pal) - 1) // len(pal)
            return (pal * times)[:nmin]

        # ---------- 主曲线（历史+模型未来） ----------
        fig, ap_final_stock = self.plot_history_and_future(
            mfa=mfa,
            data_to_plot=stock,
            subplot_dim=subplot_dim,
            linecolor_dim=linecolor_dim,
            x_array=x_array,
            x_label=x_label,
            y_label=y_label,
            title=title,
            # line_label="Historic + Modelled Future",
        )

        # ---------- pure 的颜色：更亮 + 去饱和 + 色相轻偏移 ----------
        try:
            base_cmap = list(ap_final_stock.color_map)
        except Exception:
            base_cmap = _nature_base_palette(12)

        base_cmap_hex = [
            _rgba01_to_hex(_to_rgba01(c)) if not isinstance(c, str) else c
            for c in base_cmap
        ] or _nature_base_palette(9)

        tinted_base = [_adjacent_variant_str(c) for c in base_cmap_hex]

        # 估算需要颜色数（尽量多给，避免越界）
        nmin_needed = 512
        try:
            n_guess = getattr(getattr(pure_prediction.dims, "_dict")[linecolor_dimletter], "size", None)
            if not isinstance(n_guess, int) or n_guess <= 0:
                n_guess = len(getattr(getattr(pure_prediction.dims, "_dict")[linecolor_dimletter], "labels", []))
            if isinstance(n_guess, int) and n_guess > 0:
                nmin_needed = max(2 * n_guess, 256)
        except Exception:
            pass

        pure_cmap = _extend_palette(tinted_base, nmin=nmin_needed)

        # ---------- 纯外推（点线 + 相近但更显著的颜色） ----------
        ap_pure_prediction = self.plotter_class(
            array=pure_prediction,
            intra_line_dim="Time",
            subplot_dim=subplot_dim,
            linecolor_dim=linecolor_dim,
            x_array=x_array,
            x_label=x_label,
            y_label=y_label,
            title=title,
            fig=fig,
            line_type="dot",
            # line_label="Pure Extrapolation",
            color_map=ap_final_stock.color_map * 2,
            suppress_legend=True,
        )
        fig = ap_pure_prediction.plot()

        # ---------- 轴尺度 & 风格 ----------
        if self.cfg.plotting_engine == "plotly":
            if self.cfg.use_stock["over_gdp"]:
                fig.update_xaxes(title=x_label, type="log")
            _apply_plotly_nature_style(fig)  # ← 图例已放到底部
        elif self.cfg.plotting_engine == "pyplot":
            if self.cfg.use_stock["over_gdp"]:
                for ax in fig.get_axes():
                    ax.set_xscale("log")
                    ax.set_xlabel(x_label)
            _apply_matplotlib_nature_style(fig)  # ← 图例区域留白已增大

        # ---------- 方法图例（放到底部，避免与标题冲突） ----------
        main_demo = base_cmap_hex[0]
        pure_demo = _adjacent_variant_str(main_demo)

        if self.cfg.plotting_engine == "plotly":
            try:
                import plotly.graph_objects as go
                # 两个“哑”trace形成方法层图例；位置由 _apply_plotly_nature_style 控制为图外底部
                fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                                        name="Historic + Modelled Future",
                                        line=dict(color=main_demo, width=2)))
                fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                                        name="Pure Extrapolation",
                                        line=dict(color=pure_demo, width=2, dash="dot")))
                fig.update_layout(showlegend=True)
            except Exception:
                pass
        elif self.cfg.plotting_engine == "pyplot" and mpl is not None:
            from matplotlib.lines import Line2D
            handles = [
                Line2D([0], [0], color=main_demo, lw=2, label="Historic + Modelled Future"),
                Line2D([0], [0], color=pure_demo, lw=2, ls=":", label="Pure Extrapolation"),
            ]
            try:
                # 放在底部居中；subplots_adjust 已为底部图例留出空间
                fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.04))
            except Exception:
                pass

        # ---------- 保存 ----------
        suffix = "_overGDP" if self.cfg.use_stock["over_gdp"] else "_overTime"

        self.plot_and_save_figure(
            ap_pure_prediction,
            f"stocks_extrapolation{'_overGDP' if self.cfg.use_stock['over_gdp'] else '_overTime'}.png",
            do_plot=False,
        )



    def export_stock_extrapolation(self, model: "PlasticsModel"):
        model.mfa_future.stock_handler.pure_parameters.to_df().to_csv(
            self.export_path("stock_extrapolation_parameters.csv")
        )
        model.mfa_future.stock_handler.bound_list.bound_list[0].upper_bound.to_df().to_csv(
            self.export_path("stock_extrapolation_saturationLevel.csv")
        )

    def export_stock(self, model: "PlasticsModel"):
        # 1. 获取历史数据
        mfa_h = model.mfa_historic
        inflow_h = mfa_h.stocks["in_use_historic"].inflow.sum_to(("g", "h")).to_df()
        outflow_h = mfa_h.stocks["in_use_historic"].outflow.sum_to(("g", "h")).to_df()
        stock_h = mfa_h.stocks["in_use_historic"].stock.sum_to(("g", "h")).to_df()
        
        # 2. 获取未来数据
        mfa_f = model.mfa_future
        inflow_f = mfa_f.stocks["in_use"].inflow.sum_to(("g", "t")).to_df()
        outflow_f = mfa_f.stocks["in_use"].outflow.sum_to(("g", "t")).to_df()
        stock_f = mfa_f.stocks["in_use"].stock.sum_to(("g", "t")).to_df()

        # 3. 统一列名并拼接
        def _clean(df, var_name):
            # 关键修正：重置索引，将维度转换为列
            df = df.reset_index()
            df["variable"] = var_name
            return df.rename(columns={"Historic Time": "Year", "Time": "Year"})

        pd.concat([
            _clean(inflow_h, "inflow"), _clean(outflow_h, "outflow"), _clean(stock_h, "stock"),
            _clean(inflow_f, "inflow"), _clean(outflow_f, "outflow"), _clean(stock_f, "stock")
        ]).to_csv(self.export_path("stock.csv"), index=False)

    def export_stock_by_region(self, model: "PlasticsModel"):
        # 1. 获取历史数据
        mfa_h = model.mfa_historic
        inflow_h = mfa_h.stocks["in_use_historic"].inflow.sum_to(("r", "h")).to_df()
        outflow_h = mfa_h.stocks["in_use_historic"].outflow.sum_to(("r", "h")).to_df()
        stock_h = mfa_h.stocks["in_use_historic"].stock.sum_to(("r", "h")).to_df()
        
        # 2. 获取未来数据
        mfa_f = model.mfa_future
        inflow_f = mfa_f.stocks["in_use"].inflow.sum_to(("r", "t")).to_df()
        outflow_f = mfa_f.stocks["in_use"].outflow.sum_to(("r", "t")).to_df()
        stock_f = mfa_f.stocks["in_use"].stock.sum_to(("r", "t")).to_df()

        # 3. 统一列名并拼接
        def _clean(df, var_name):
            # 关键修正：重置索引，将维度转换为列
            df = df.reset_index()
            df["variable"] = var_name
            return df.rename(columns={"Historic Time": "Year", "Time": "Year"})

        pd.concat([
            _clean(inflow_h, "inflow"), _clean(outflow_h, "outflow"), _clean(stock_h, "stock"),
            _clean(inflow_f, "inflow"), _clean(outflow_f, "outflow"), _clean(stock_f, "stock")
        ]).to_csv(self.export_path("stock_by_region.csv"), index=False)

    def export_eol_data_by_region_and_year(
        self, mfa: fd.MFASystem, output_path: str = "eol_by_region_year.csv"
    ):
        eol_data = (
            mfa.flows["eol => collected"]
            + mfa.flows["waste_market => collected"]
            - mfa.flows["collected => waste_market"]
        )
        df = eol_data.sum_to(("t", "r", "m")).to_df(index=True)
        df.to_csv(self.export_path(output_path), index=True)

    def export_use_data_by_region_and_year(
        self, mfa: fd.MFASystem, output_path: str = "use_by_region_year.csv"
    ):
        df = mfa.flows["fabrication => use"].sum_to(("t", "r")).to_df(index=True)
        df.to_csv(self.export_path(output_path), index=True)

    def export_production_data_by_region_and_year(
        self, mfa: fd.MFASystem, output_path: str = "production_by_region_year.csv"
    ):
        df = mfa.flows["virgin => processing"].sum_to(("t", "r")).to_df(index=True) + \
            mfa.flows["virgin => primary_market"].sum_to(("t", "r")).to_df(index=True) + \
            mfa.flows["reclmech => processing"].sum_to(("t", "r")).to_df(index=True)
            
        df.to_csv(self.export_path(output_path), index=True)

    def export_recycling_data_by_region_and_year(
        self, mfa: fd.MFASystem, output_path: str = "recycling_by_region_year.csv"
    ):
        recl_data = mfa.flows["collected => reclmech"] + mfa.flows["collected => reclchem"]
        df = recl_data.sum_to(("t", "r", "m")).to_df(index=True)
        df.to_csv(self.export_path(output_path), index=True)

    def export_mfa(self, model: "PlasticsModel"):
        super().export_mfa(mfa=model.mfa_future)
        if self.do_export.iamc:
            self.write_iamc(mfa=model.mfa_future)
        if self.do_export.csv:
            self.export_eol_data_by_region_and_year(mfa=model.mfa_future)
            self.export_use_data_by_region_and_year(mfa=model.mfa_future)
            self.export_recycling_data_by_region_and_year(mfa=model.mfa_future)
            self.export_stock_extrapolation(model=model)
            self.export_stock(model=model)
            self.export_stock_by_region(model=model)
            

    def write_iamc(self, mfa: fd.MFASystem):

        model = "REMIND 3.0"
        scenario = "SSP2_NPi"
        constants = {"model": model, "scenario": scenario}

        # production
        ## primary production
        prod_virgin = (
            mfa.flows["virginfoss => virgin"]
            + mfa.flows["virginbio => virgin"]
            + mfa.flows["virgindaccu => virgin"]
            + mfa.flows["virginccu => virgin"]
        )
        prod_virgin_df = self.to_iamc_df(prod_virgin.sum_to(("t", "r")))
        prod_virgin_idf = pyam.IamDataFrame(
            prod_virgin_df,
            variable="Production|Chemicals|Plastics|Primary",
            unit="Mt/yr",
            **constants,
        )
        ## secondary production
        prod_recl = mfa.flows["reclmech => processing"] + mfa.flows["reclchem => virgin"]
        prod_recl_df = self.to_iamc_df(prod_recl.sum_to(("t", "r")))
        prod_recl_idf = pyam.IamDataFrame(
            prod_recl_df,
            variable="Production|Chemicals|Plastics|Secondary",
            unit="Mt/yr",
            **constants,
        )
        ## total production
        prod_idf = pyam.concat(
            [
                prod_virgin_idf,
                prod_recl_idf,
            ]
        )
        prod_idf.aggregate(
            variable="Production|Chemicals|Plastics",
            append=True,
        )

        # demand
        ## demand by good
        plastic_demand_by_good = mfa.stocks["in_use"].inflow.sum_to(("t", "r", "g"))
        demand_df = self.to_iamc_df(plastic_demand_by_good)
        demand_df["variable"] = "Material Demand|Chemicals|Plastics|" + demand_df["Good"]
        demand_df = demand_df.drop(columns=["Good"])
        demand_idf = pyam.IamDataFrame(
            demand_df,
            unit="Mt/yr",
            **constants,
        )
        demand_idf.aggregate(
            variable="Material Demand|Chemicals|Plastics",
            append=True,
        )
        ## demand by origin (primary/secondary) and good
        recycled = prod_recl / (prod_virgin + prod_recl)
        ### primary
        plastic_demand_virgin = mfa.stocks["in_use"].inflow * (1 - recycled)
        demand_virgin_df = self.to_iamc_df(plastic_demand_virgin.sum_to(("t", "r", "g")))
        demand_virgin_df["variable"] = (
            "Material Demand|Chemicals|Plastics|Primary|" + demand_virgin_df["Good"]
        )
        demand_virgin_df = demand_virgin_df.drop(columns=["Good"])
        demand_virgin_idf = pyam.IamDataFrame(
            demand_virgin_df,
            unit="Mt/yr",
            **constants,
        )
        demand_virgin_idf.aggregate(
            variable="Material Demand|Chemicals|Plastics|Primary",
            append=True,
        )
        ### secondary
        plastic_demand_recl = mfa.stocks["in_use"].inflow * recycled
        demand_recl_df = self.to_iamc_df(plastic_demand_recl.sum_to(("t", "r", "g")))
        demand_recl_df["variable"] = (
            "Material Demand|Chemicals|Plastics|Secondary|" + demand_recl_df["Good"]
        )
        demand_recl_df = demand_recl_df.drop(columns=["Good"])
        demand_recl_idf = pyam.IamDataFrame(
            demand_recl_df,
            unit="Mt/yr",
            **constants,
        )
        demand_recl_idf.aggregate(
            variable="Material Demand|Chemicals|Plastics|Secondary",
            append=True,
        )
        demand_origin_idf = pyam.concat(
            [
                demand_virgin_idf,
                demand_recl_idf,
            ]
        )
        # demand_origin_idf.aggregate(
        #     variable="Material Demand|Chemicals|Plastics",
        #     append=True,
        # )

        idf = pyam.concat(
            [
                prod_idf,
                demand_idf,
                demand_origin_idf,
            ]
        )
        idf.aggregate_region(
            variable=idf.variable,
            region="World",
            append=True,
        )

        idf.to_excel(self.export_path(f"output_iamc.xlsx"))

    @staticmethod
    def to_iamc_df(array: fd.FlodymArray):
        time_items = list(range(2025, 2101))  # TODO: more flexible
        time_out = fd.Dimension(name="Time Out", letter="O", items=time_items)
        df = array[{"t": time_out}].to_df(dim_to_columns="Time Out", index=False)
        df = df.rename(columns={"Region": "region"})
        return df
