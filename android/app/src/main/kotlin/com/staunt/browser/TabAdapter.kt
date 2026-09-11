package com.staunt.browser

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class TabAdapter(
    private val tabs: List<TabData>,
    private val activeTabId: () -> String?,
    private val onTabSelected: (TabData) -> Unit,
    private val onTabClosed: (TabData) -> Unit
) : RecyclerView.Adapter<TabAdapter.TabViewHolder>() {

    class TabViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val tvTitle: TextView = view.findViewById(R.id.tvTitle)
        val ivFavicon: ImageView = view.findViewById(R.id.ivFavicon)
        val ivThumbnail: ImageView = view.findViewById(R.id.ivThumbnail)
        val btnClose: ImageButton = view.findViewById(R.id.btnClose)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): TabViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_tab, parent, false)
        return TabViewHolder(view)
    }

    override fun onBindViewHolder(holder: TabViewHolder, position: Int) {
        val tab = tabs[position]
        holder.tvTitle.text = if (tab.title.isNotBlank()) tab.title else (if (tab.url.isNotBlank()) tab.url else "New Tab")
        
        if (tab.favicon != null) {
            holder.ivFavicon.setImageBitmap(tab.favicon)
        } else {
            holder.ivFavicon.setImageResource(R.drawable.ic_staunt_globe)
        }

        holder.itemView.alpha = if (tab.id == activeTabId()) 1.0f else 0.75f

        holder.itemView.setOnClickListener {
            onTabSelected(tab)
        }

        holder.btnClose.setOnClickListener {
            onTabClosed(tab)
        }
    }

    override fun getItemCount(): Int = tabs.size
}
