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
        "waste_imports": "Wastes Imports",
        "waste_exports": "Wastes Exports",
        "waste_market": "Waste Market",
        "primary_imports": "Prim Imports",
        "primary_exports": "Prim Exports",
        "primary_market": "Prim Market",
        "intermediate_imports": "Inter Imports",
        "intermediate_exports": "Inter Exports",
        "intermediate_market": "Inter Market",
        "final_imports": "Final Imports",
        "final_exports": "Final Exports",
        "good_market": "Good Market",
    }

    def visualize_results(self, model: "PlasticsModel"):
        if not self.cfg.do_visualize:
            return
        
        self.export_eol_data_by_region_and_year(mfa=model.mfa_future)
        self.export_use_data_by_region_and_year(mfa=model.mfa_future)
        self.export_recycling_data_by_region_and_year(mfa=model.mfa_future)
        self.export_stock_extrapolation(model=model)
        self.export_stock(mfa=model.mfa_historic)
        
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
            primary_production = model.mfa_future.flows["virginfoss => virgin"] + model.mfa_future.flows["virginbio => virgin"] + model.mfa_future.flows["virgindaccu => virgin"] + model.mfa_future.flows["virginccu => virgin"]
            self.visualize_flow(mfa=model.mfa_future, flow=primary_production, name="Primary production", subplot_dim="Material")
            self.visualize_flow(mfa=model.mfa_future, flow=model.mfa_future.flows["recl => fabrication"], name="Secondary production", subplot_dim="Material")
            self.visualize_flow(mfa=model.mfa_future, flow=model.mfa_future.stocks["in_use"].inflow, name="Demand", subplot_dim="Region", linecolor_dim="Good")

        self.stop_and_show()

    def visualize_flow(
        self, mfa: fd.MFASystem, flow: fd.Flow, name: str, subplot_dim = None, linecolor_dim = None
    ):

        x_array = None
        x_label = "Year"
        y_label = "Flow [Mt]"
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
        sum_dims = tuple(x for x in flow.dims.letters if x not in (subplot_dimletter, linecolor_dimletter, "t"))
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

        # ========= NS-Plastics 基础色（你的版本） =========
        NS_PLASTICS_SEED = [
            "#F0857B",  # soft pink
            "#FEE026",  # muted blue
            "#95CF93",  # soft green
            "#BF96C2",  # muted purple
            "#F6B176",  # soft orange
            "#87B2D5",  # warm yellow
            "#CA9A7E",  # tan/brown
            "#F5B1CA",  # pale pink
        ]

        # —— 可调参数（保持你当前数值） ——
        SAT_BOOST_LINES = 1.5    # 折线饱和提升
        SAT_BOOST_AREAS = 1.0  # 面积饱和提升
        LIGHTEN_HIST    = 0.22   # 历史线提亮
        DESAT_HIST      = 0.85   # 历史线去饱和
        DARKEN_ROUND    = 0.06   # 扩展色板逐轮变暗
        TOP_PAD         = 0.90   # matplotlib 顶部留白
        BOTTOM_PAD      = 0.18   # matplotlib 底部留白

        # ========= 从允许的位置读取 Region =========
        def _cfg_get(path, default=None):
            obj = self.cfg
            for k in path:
                try:
                    obj = obj[k] if isinstance(obj, dict) else getattr(obj, k)
                except Exception:
                    return default
            return obj

        # 仅从 schema 允许的位置读取，避免 pydantic 报错
        region_sel = _cfg_get(["visualization", "sankey", "slice_dict", "r"])

        # ========= 颜色 & 工具（全部返回 hex） =========
        def _hex_to_rgb01(hx: str):
            hx = hx.strip().lstrip("#")
            return int(hx[0:2],16)/255.0, int(hx[2:4],16)/255.0, int(hx[4:6],16)/255.0

        def _rgb01_to_hex(r,g,b):
            clamp=lambda x:max(0,min(1,x))
            return "#{:02x}{:02x}{:02x}".format(
                int(round(clamp(r)*255)), int(round(clamp(g)*255)), int(round(clamp(b)*255))
            )

        def _sat_light(hx: str, sat_mult=1.0, light_add=0.0):
            r,g,b=_hex_to_rgb01(hx); h,l,s=colorsys.rgb_to_hls(r,g,b)
            l=min(1.0, l+light_add); s=max(0.0, min(1.0, s*sat_mult))
            r2,g2,b2=colorsys.hls_to_rgb(h,l,s)
            return _rgb01_to_hex(r2,g2,b2)

        def _darken(hx: str, delta=0.08):
            r,g,b=_hex_to_rgb01(hx)
            return _rgb01_to_hex(r-delta, g-delta, b-delta)

        def _expand(seed, nmin=256, dark_step=DARKEN_ROUND):
            """扩展色板长度，避免 color_map 越界。"""
            if not seed: seed=["#7FB2DE"]
            out=[]; rounds=(nmin+len(seed)-1)//len(seed)
            for k in range(rounds):
                tweak=min(0.18, dark_step*k)
                out += [_darken(c, tweak) for c in seed]
            return out[:nmin]

        def _long_black_cmap(n=2048):
            """提供足够长的黑色 color_map，避免 add_line 时 i_color 越界。"""
            return ["#000000"] * n

        # ========= 维度安全工具（核心：消除多余维度） =========
        def _sum_over_safe(arr, dims):
            """对给定 dimletters 逐个尝试 sum_over，忽略不存在的维度。"""
            for d in dims:
                try:
                    arr = arr.sum_over((d,))
                except Exception:
                    pass
            return arr

        def _select_region_or_global(arr):
            """若 cfg 指定 r 则选该 Region；否则对 r 求和为 Global。最后再保险去 r。"""
            if region_sel:
                # 常见 API；失败则回退到对 r 求和
                for meth in ("sel", "select", "slice"):
                    try:
                        return getattr(arr, meth)({"r": region_sel})
                    except Exception:
                        pass
                try:
                    labels = getattr(getattr(arr.dims, "_dict")["r"], "labels", [])
                    if region_sel in labels:
                        idx = labels.index(region_sel)
                        try:
                            return arr.isel({"r": idx})
                        except Exception:
                            pass
                except Exception:
                    pass
            return _sum_over_safe(arr, ("r",))

        # —— 基色 / 历史线 / 面积色 —— 
        base_colors_raw = _expand(NS_PLASTICS_SEED, nmin=512)
        base_colors     = [_sat_light(c, sat_mult=SAT_BOOST_LINES, light_add=0.0) for c in base_colors_raw]
        hist_colors     = [_sat_light(c, sat_mult=DESAT_HIST,    light_add=LIGHTEN_HIST) for c in base_colors]
        stacked_colors  = [_sat_light(c, sat_mult=SAT_BOOST_AREAS, light_add=-0.02)     for c in base_colors]

        # ========= 版式风格 =========
        def _apply_plotly_style(fig, bottom_legend=True):
            legend_cfg = dict(orientation="h", xanchor="left", x=0.0)
            if bottom_legend:
                legend_cfg.update(yanchor="top", y=-0.12)
                margins = dict(l=60, r=26, t=64, b=96)
            else:
                legend_cfg.update(yanchor="bottom", y=1.02)
                margins = dict(l=60, r=26, t=72, b=58)
            fig.update_layout(
                template="simple_white",
                font=dict(family="Arial, DejaVu Sans, Helvetica", size=11),
                title=dict(font=dict(size=14), y=0.98),
                margin=margins,
                legend=legend_cfg,
                showlegend=True,
            )
            fig.update_xaxes(showline=True, linewidth=1, linecolor="#333333",
                            mirror=False, zeroline=False, gridcolor="rgba(0,0,0,0.08)", ticklen=4)
            fig.update_yaxes(showline=True, linewidth=1, linecolor="#333333",
                            mirror=False, zeroline=False, gridcolor="rgba(0,0,0,0.08)", ticklen=4)

        def _apply_mpl_style(fig, bottom_legend=True):
            try:
                import matplotlib as mpl
            except Exception:
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
                "xtick.major.size": 3.5, "xtick.major.width": 0.9,
                "ytick.major.size": 3.5, "ytick.major.width": 0.9,
                "lines.linewidth": 1.9,
                "savefig.dpi": 300, "figure.dpi": 120,
            }
            with mpl.rc_context(rc):
                for ax in fig.get_axes():
                    for side in ["top","right"]:
                        ax.spines[side].set_visible(False)
                try:
                    fig.subplots_adjust(top=TOP_PAD, bottom=BOTTOM_PAD)
                except Exception:
                    pass

        def _style(fig, bottom_legend=True):
            if getattr(self.cfg, "plotting_engine", "plotly") == "plotly":
                _apply_plotly_style(fig, bottom_legend=bottom_legend)
            else:
                _apply_mpl_style(fig, bottom_legend=bottom_legend)

        # ========= 1) 折线：Modelled vs Historic =========
        modeled_array = _select_region_or_global(mfa.stocks["in_use"].inflow)
        modeled_array = _sum_over_safe(modeled_array, ("m", "e", "r"))  # 保留 dims: [t,g]
        ap_modeled = self.plotter_class(
            array=modeled_array,
            intra_line_dim="Time",
            subplot_dim="Good",
            line_label="Modelled",
            display_names=self._display_names,
            color_map=base_colors,
        )
        fig = ap_modeled.plot()

        hist_array = _select_region_or_global(mfa.parameters["production"])
        hist_array = _sum_over_safe(hist_array, ("r",))                # 保留 dims: [th,g] 这里 th=Historic Time
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
        _style(fig, bottom_legend=True)

        # 方法图例（底部，确保一定出现）
        try:
            if getattr(self.cfg, "plotting_engine", "plotly") == "plotly":
                import plotly.graph_objects as go
                fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                                        name="Modelled", line=dict(color=base_colors[0], width=2)))
                fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                                        name="Historic", line=dict(color=hist_colors[0], width=2, dash="dot")))
                fig.update_layout(showlegend=True)
            else:
                from matplotlib.lines import Line2D
                handles = [
                    Line2D([0],[0], color=base_colors[0], lw=2, label="Modelled"),
                    Line2D([0],[0], color=hist_colors[0], lw=2, ls=":", label="Historic"),
                ]
                try:
                    fig.legend(handles=handles, loc="lower center", ncol=2,
                            frameon=False, bbox_to_anchor=(0.5, 0.02))
                except Exception:
                    pass
        except Exception:
            pass

        self.plot_and_save_figure(ap_historic, "demand.png")

        # ========= 2) 堆叠面积：Inflow / Outflow / Stock + 黑色 inflow 总折线 =========
        inflow_allr  = _select_region_or_global(mfa.stocks["in_use"].inflow)
        outflow_allr = _select_region_or_global(mfa.stocks["in_use"].outflow)
        stock_allr   = _select_region_or_global(mfa.stocks["in_use"].stock)

        inflow = _sum_over_safe(inflow_allr,  ("m", "e"))  # dims: [t,g]
        outflow = _sum_over_safe(outflow_allr, ("m", "e")) # dims: [t,g]
        stock  = _sum_over_safe(stock_allr,   ("m", "e"))  # dims: [t,g]

        # Good 维度索引用于 cumsum
        good_dim = inflow.dims.index("g")
        inflow_cumsum  = inflow.apply(np.cumsum, kwargs={"axis": good_dim})
        outflow_cumsum = outflow.apply(np.cumsum, kwargs={"axis": good_dim})
        stock_cumsum   = stock .apply(np.cumsum, kwargs={"axis": good_dim})

        # 总 inflow 折线（仅保留 Time）
        inflow_total_line = _sum_over_safe(inflow, ("g", "r", "m", "e"))  # dims: [t]

        # —— Inflow 面积 + 黑线 —— 
        ap_inflow = self.plotter_class(
            array=inflow_cumsum,
            intra_line_dim="Time",
            linecolor_dim="Good",
            chart_type="area",
            display_names=self._display_names,
            title="Inflow [Mt]" + (f" — {region_sel}" if region_sel else " — Global"),
            color_map=stacked_colors,
        )
        fig_inflow = ap_inflow.plot()
        ap_inflow_line = self.plotter_class(
            array=inflow_total_line,
            intra_line_dim="Time",
            fig=fig_inflow,
            line_label="Inflow (total)",
            color_map=_long_black_cmap(),  # 关键：给足够长的黑色列表，避免越界
        )
        fig_inflow = ap_inflow_line.plot()
        _style(fig_inflow, bottom_legend=True)
        self.plot_and_save_figure(ap_inflow_line, "inflow_stacked.png", do_plot=False)

        # —— Outflow 面积 + 黑线（仍用 inflow 总线）——
        ap_outflow = self.plotter_class(
            array=outflow_cumsum,
            intra_line_dim="Time",
            linecolor_dim="Good",
            chart_type="area",
            display_names=self._display_names,
            title="Outflow [Mt]" + (f" — {region_sel}" if region_sel else " — Global"),
            color_map=stacked_colors,
        )
        fig_outflow = ap_outflow.plot()
        ap_outflow_line = self.plotter_class(
            array=inflow_total_line,
            intra_line_dim="Time",
            fig=fig_outflow,
            line_label="Inflow (total)",
            color_map=_long_black_cmap(),
        )
        fig_outflow = ap_outflow_line.plot()
        _style(fig_outflow, bottom_legend=True)
        self.plot_and_save_figure(ap_outflow_line, "outflow_stacked.png", do_plot=False)

        # —— Stock 面积 + 黑线（仍用 inflow 总线）——
        ap_stock = self.plotter_class(
            array=stock_cumsum,
            intra_line_dim="Time",
            linecolor_dim="Good",
            chart_type="area",
            display_names=self._display_names,
            title="Stock [Mt]" + (f" — {region_sel}" if region_sel else " — Global"),
            color_map=stacked_colors,
        )
        fig_stock = ap_stock.plot()
        ap_stock_line = self.plotter_class(
            array=inflow_total_line,
            intra_line_dim="Time",
            fig=fig_stock,
            line_label="Inflow (total)",
            color_map=_long_black_cmap(),
        )
        fig_stock = ap_stock_line.plot()
        _style(fig_stock, bottom_legend=True)
        self.plot_and_save_figure(ap_stock_line, "stock_stacked.png", do_plot=False)



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

    def visualize_sankey(self, mfa: fd.MFASystem):
        # Define colors for each stage
        production_color = "#EDC948"
        use_color = "#9EC3D5"
        eol_color = "#499894"
        recycle_color = "#86BCB6"
        emission_color = "#E15759"
        trade_color = "#D37295"

        # Initialize default flow color mapping
        flow_color_dict = {"default": production_color}

        # Assign colors to 'use' flows
        flow_color_dict.update(
            {
                fn: use_color
                for fn, f in mfa.flows.items()
                if f.from_process.name == "use" or f.to_process.name == "use"
            }
        )

        # Assign colors to end-of-life flows
        flow_color_dict.update(
            {
                fn: eol_color
                for fn, f in mfa.flows.items()
                if f.from_process.name in ("eol", "collected")
            }
        )

        # Assign colors to emission flows
        flow_color_dict.update(
            {
                fn: emission_color
                for fn, f in mfa.flows.items()
                if f.to_process.name
                in ("atmosphere", "mismanaged", "incineration", "uncontrolled", "emission")
            }
        )

        # Assign colors to recycling flows
        flow_color_dict.update(
            {
                fn: recycle_color
                for fn, f in mfa.flows.items()
                if f.from_process.name in ("reclmech", "reclchem")
                or f.to_process.name in ("reclmech", "reclchem")
            }
        )

        # Update Sankey layout configuration
        self.cfg.sankey.update(
            {
                "valueformat": ".2s",  # scientific notation, two significant digits
                "node_pad": 15,  # padding between nodes
                "node_thickness": 20,  # node thickness
                "arrangement": "snap",  # reduce crossings by snapping nodes
                "flow_color_dict": flow_color_dict,
                "node_color_dict": {"default": "gray", "use": "black"},
            }
        )

        # Prepare display names and generate the Sankey diagram
        display_names_fmt = {k: f"<b>{v}</b>" for k, v in self._display_names.items()}
        plotter = fde.PlotlySankeyPlotter(
            mfa=mfa, display_names=display_names_fmt, **self.cfg.sankey
        )
        fig = plotter.plot()

        # Add legend entries
        legend_entries = [
            (production_color, "Production"),
            (eol_color, "End-of-Life"),
            (recycle_color, "Use"),
            (emission_color, "Losses"),
            (trade_color, "Trade"),
        ]
        for color, label in legend_entries:
            fig.add_trace(
                go.Scatter(
                    mode="markers",
                    x=[None],
                    y=[None],
                    marker=dict(size=10, color=color, symbol="square"),
                    name=label,
                )
            )

        # Final layout adjustments and display
        fig.update_layout(
            font_size=18, showlegend=True, plot_bgcolor="rgba(0,0,0,0)", font_color="black"
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)

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
        title = "Stock Extrapolation: Historic and Projected vs Pure Prediction"

        # ---------- 维度 ----------
        dimlist = ["t"]
        if subplot_dim is not None:
            subplot_dimletter = next(d.letter for d in mfa.dims.dim_list if d.name == subplot_dim)
            dimlist.append(subplot_dimletter)
        if linecolor_dim is not None:
            linecolor_dimletter = next(d.letter for d in mfa.dims.dim_list if d.name == linecolor_dim)
            dimlist.append(linecolor_dimletter)

        other_dimletters = tuple(letter for letter in stock.dims.letters if letter not in dimlist)
        stock = stock.sum_over(other_dimletters) * 1_000_000
        other_dimletters = tuple(
            letter for letter in model.mfa_future.stock_handler.pure_prediction.dims.letters
            if letter not in dimlist
        )
        pure_prediction = model.mfa_future.stock_handler.pure_prediction.sum_over(other_dimletters) * 1_000_000

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
            color_map=pure_cmap,
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
        self.plot_and_save_figure(
            ap_pure_prediction,
            f"stocks_extrapolation{'_overGDP' if self.cfg.use_stock["over_gdp"] else '_overTime'}.png",
            do_plot=False,
        )



    def export_stock_extrapolation(self, model: "PlasticsModel"):
        model.mfa_future.stock_handler.pure_parameters.to_df().to_csv(self.export_path("stock_extrapolation_parameters.csv"))
        model.mfa_future.stock_handler.bound_list.bound_list[0].upper_bound.to_df().to_csv(self.export_path("stock_extrapolation_saturationLevel.csv"))

    def export_stock(self, mfa: fd.MFASystem):
        inflow = mfa.stocks["in_use_historic"].inflow.sum_to(('g','h')).to_df()
        inflow["variable"] = "inflow"
        outflow = mfa.stocks["in_use_historic"].outflow.sum_to(('g','h')).to_df()
        outflow["variable"] = "outflow"
        stock = mfa.stocks["in_use_historic"].stock.sum_to(('g','h')).to_df()
        stock["variable"] = "stock"
        pd.concat([inflow, outflow, stock]).to_csv(self.export_path("stock.csv"))

    def export_eol_data_by_region_and_year(
        self, mfa: fd.MFASystem, output_path: str = "eol_by_region_year.csv"
    ):
        eol_data = (
            mfa.flows["eol => collected"]
            + mfa.flows["waste_imports => collected"]
            - mfa.flows["collected => waste_exports"]
        )
        df = eol_data.sum_to(("t", "r", "m")).to_df(index=True)
        df.to_csv(self.export_path(output_path), index=True)

    def export_use_data_by_region_and_year(
        self, mfa: fd.MFASystem, output_path: str = "use_by_region_year.csv"
    ):
        df = mfa.flows["fabrication => use"].sum_to(("t", "r")).to_df(index=True)
        df.to_csv(self.export_path(output_path), index=True)

    def export_recycling_data_by_region_and_year(
        self, mfa: fd.MFASystem, output_path: str = "recycling_by_region_year.csv"
    ):
        recl_data = mfa.flows["collected => reclmech"] + mfa.flows["collected => reclchem"]
        df = recl_data.sum_to(("t", "r", "m")).to_df(index=True)
        df.to_csv(self.export_path(output_path), index=True)

    def write_iamc(self, mfa: fd.MFASystem):

        model = "REMIND 3.0"
        scenario = "SSP2_NPi"
        constants = {"model": model, "scenario": scenario}

        # production
        ## primary production
        prod_virgin = (mfa.flows["virginfoss => virgin"] + 
                       mfa.flows["virginbio => virgin"] + 
                       mfa.flows["virgindaccu => virgin"] + 
                       mfa.flows["virginccu => virgin"])
        prod_virgin_df = self.to_iamc_df(prod_virgin.sum_to(('t','r')))
        prod_virgin_idf = pyam.IamDataFrame(
            prod_virgin_df,
            variable="Production|Chemicals|Plastics|Primary",
            unit="Mt/yr",
            **constants,
        )
        ## secondary production
        prod_recl = (mfa.flows["reclmech => fabrication"] + 
                     mfa.flows["reclchem => processing"])
        prod_recl_df = self.to_iamc_df(prod_recl.sum_to(('t','r')))
        prod_recl_idf = pyam.IamDataFrame(
            prod_recl_df,
            variable="Production|Chemicals|Plastics|Secondary",
            unit="Mt/yr",
            **constants,
        )
        ## total production
        prod_idf = pyam.concat([
            prod_virgin_idf,
            prod_recl_idf,
        ])
        prod_idf.aggregate(
            variable="Production|Chemicals|Plastics",
            append=True,
        )

        # demand
        ## demand by good
        plastic_demand_by_good = mfa.stocks["in_use"].inflow.sum_to(('t','r','g'))
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
        demand_virgin_df = self.to_iamc_df(plastic_demand_virgin.sum_to(('t','r','g')))
        demand_virgin_df["variable"] = "Material Demand|Chemicals|Plastics|Primary|" + demand_virgin_df["Good"]
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
        demand_recl_df = self.to_iamc_df(plastic_demand_recl.sum_to(('t','r','g')))
        demand_recl_df["variable"] = "Material Demand|Chemicals|Plastics|Secondary|" + demand_recl_df["Good"]
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
        demand_origin_idf = pyam.concat([
            demand_virgin_idf,
            demand_recl_idf,
        ])  
        # demand_origin_idf.aggregate(
        #     variable="Material Demand|Chemicals|Plastics",
        #     append=True,
        # )              
        
        idf = pyam.concat([
            prod_idf,
            demand_idf,
            demand_origin_idf,
        ])
        idf.aggregate_region(
            variable=idf.variable,
            region="World",
            append=True,
        )

        idf.to_excel(self.export_path(f"output_iamc.xlsx"))


    @staticmethod
    def to_iamc_df(array: fd.FlodymArray):
        time_items = list(range(2025, 2101)) # TODO: more flexible
        time_out = fd.Dimension(name="Time Out", letter="O", items=time_items)
        df = array[{"t": time_out}].to_df(dim_to_columns="Time Out", index=False)
        df = df.rename(columns={"Region": "region"})
        return df
