import type { EditorPlugin, PluginRegistry, EditorType } from './types'

/**
 * PluginManager - Singleton class for managing editor plugins
 * Supports plugin registration, lazy loading, and lifecycle hooks
 */
class PluginManagerClass {
  private plugins: PluginRegistry = {}
  private loadedPlugins: Set<string> = new Set()
  private loadingPromises: Map<string, Promise<EditorPlugin | undefined>> = new Map()

  /**
   * Register a plugin
   * @param plugin - The plugin to register
   */
  register(plugin: EditorPlugin): void {
    if (!plugin.type) {
      console.error('[PluginManager] Plugin must have a type property')
      return
    }

    if (this.plugins[plugin.type]) {
      console.warn(`[PluginManager] Plugin "${plugin.type}" is already registered. Overwriting.`)
    }

    this.plugins[plugin.type] = plugin
    console.log(`[PluginManager] Plugin "${plugin.name}" (${plugin.type}) registered successfully`)
  }

  /**
   * Get a registered plugin by type
   * @param type - The editor type
   * @returns The plugin or undefined if not found
   */
  getPlugin(type: EditorType): EditorPlugin | undefined {
    return this.plugins[type]
  }

  /**
   * Lazy load a plugin by type
   * Calls the plugin's onLoad lifecycle hook
   * @param type - The editor type
   * @returns Promise resolving to the plugin or undefined
   */
  async loadPlugin(type: EditorType): Promise<EditorPlugin | undefined> {
    // Return if already loaded
    if (this.isLoaded(type)) {
      return this.plugins[type]
    }

    // Return existing loading promise to prevent duplicate loads
    if (this.loadingPromises.has(type)) {
      return this.loadingPromises.get(type)!
    }

    const plugin = this.plugins[type]
    if (!plugin) {
      console.warn(`[PluginManager] Plugin "${type}" not found`)
      return undefined
    }

    // Create loading promise
    const loadPromise = this._loadPluginInternal(plugin)
    this.loadingPromises.set(type, loadPromise)

    try {
      const result = await loadPromise
      return result
    } finally {
      this.loadingPromises.delete(type)
    }
  }

  /**
   * Internal method to handle plugin loading
   * @param plugin - The plugin to load
   */
  private async _loadPluginInternal(plugin: EditorPlugin): Promise<EditorPlugin | undefined> {
    try {
      // Call onLoad hook if exists
      if (plugin.onLoad) {
        await plugin.onLoad()
      }

      const pluginType = plugin.type || plugin.id
      if (pluginType) {
        this.loadedPlugins.add(pluginType as EditorType)
      }
      console.log(`[PluginManager] Plugin "${plugin.name}" (${pluginType}) loaded successfully`)
      return plugin
    } catch (error) {
      console.error(`[PluginManager] Failed to load plugin "${plugin.name}":`, error)
      throw error
    }
  }

  /**
   * Unload a plugin by type
   * Calls the plugin's onUnload lifecycle hook
   * @param type - The editor type
   */
  async unloadPlugin(type: EditorType): Promise<void> {
    const plugin = this.plugins[type]

    if (!plugin) {
      console.warn(`[PluginManager] Plugin "${type}" not found`)
      return
    }

    if (!this.isLoaded(type)) {
      console.warn(`[PluginManager] Plugin "${type}" is not loaded`)
      return
    }

    try {
      // Call onUnload hook if exists
      if (plugin.onUnload) {
        await plugin.onUnload()
      }

      this.loadedPlugins.delete(type)
      console.log(`[PluginManager] Plugin "${plugin.name}" (${plugin.type}) unloaded successfully`)
    } catch (error) {
      console.error(`[PluginManager] Failed to unload plugin "${plugin.name}":`, error)
      throw error
    }
  }

  /**
   * Get all registered plugins
   * @returns Array of all registered plugins
   */
  getAllPlugins(): EditorPlugin[] {
    return Object.values(this.plugins).filter((plugin): plugin is EditorPlugin => plugin !== undefined)
  }

  /**
   * Check if a plugin is loaded
   * @param type - The editor type
   * @returns True if the plugin is loaded
   */
  isLoaded(type: EditorType): boolean {
    return this.loadedPlugins.has(type)
  }

  /**
   * Initialize all registered plugins
   * Loads all plugins in parallel
   */
  async initPlugins(): Promise<void> {
    const pluginTypes = Object.keys(this.plugins) as EditorType[]

    if (pluginTypes.length === 0) {
      console.log('[PluginManager] No plugins to initialize')
      return
    }

    console.log(`[PluginManager] Initializing ${pluginTypes.length} plugins...`)

    const loadPromises = pluginTypes.map(async (type) => {
      try {
        await this.loadPlugin(type)
      } catch (error) {
        // Log error but don't fail the entire initialization
        console.error(`[PluginManager] Failed to initialize plugin "${type}":`, error)
      }
    })

    await Promise.all(loadPromises)
    console.log(`[PluginManager] Plugin initialization complete. ${this.loadedPlugins.size}/${pluginTypes.length} plugins loaded`)
  }

  /**
   * Unload all loaded plugins
   */
  async unloadAll(): Promise<void> {
    const loadedTypes = Array.from(this.loadedPlugins) as EditorType[]
    const unloadPromises = loadedTypes.map((type) => this.unloadPlugin(type))
    await Promise.all(unloadPromises)
  }

  /**
   * Clear all registered plugins
   * Useful for testing or hot module replacement
   */
  clear(): void {
    this.plugins = {}
    this.loadedPlugins.clear()
    this.loadingPromises.clear()
  }
}

// Export singleton instance
export const PluginManager = new PluginManagerClass()
export default PluginManager
